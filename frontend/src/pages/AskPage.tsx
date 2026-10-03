import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api'
import { TurnCard, type Turn } from '../components/TurnCard'
import { useDocuments, useLlmConfig, useRagConfig } from '../hooks'
import { streamQuery } from '../sse'
import type { LLMSettings } from '../types'

function modelLabel(llm: LLMSettings | undefined): string {
  if (!llm) return 'model'
  if (llm.provider === 'ollama') return `Ollama · ${llm.ollama.model}`
  if (llm.provider === 'claude') return `Claude · ${llm.claude.model}`
  return 'Echo (no model)'
}

export default function AskPage() {
  const rag = useRagConfig()
  const llm = useLlmConfig()
  const docs = useDocuments()
  const settings = rag.data?.settings

  // The conversation lives only in memory: refreshing the page clears it. Nothing is stored anywhere.
  const [turns, setTurns] = useState<Turn[]>([])
  const [question, setQuestion] = useState('')
  const [retrievalOnly, setRetrievalOnly] = useState(false)
  const [showPrompt, setShowPrompt] = useState(false)
  const [busy, setBusy] = useState(false)
  const abort = useRef<AbortController | null>(null)
  const nextId = useRef(1)
  const input = useRef<HTMLTextAreaElement>(null)
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [turns.length])

  async function ask(text: string) {
    const id = nextId.current++
    const startedAt = Date.now()
    const turn: Turn = {
      id, question: text, answer: '', sources: null, prompt: null, error: null, status: 'streaming',
      retrievalOnly, by: modelLabel(llm.data), startedAt, elapsedMs: null,
    }
    setTurns((ts) => [...ts, turn])
    const update = (patch: Partial<Turn> | ((t: Turn) => Partial<Turn>)) =>
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, ...(typeof patch === 'function' ? patch(t) : patch) } : t)))

    const controller = new AbortController()
    abort.current = controller
    setBusy(true)
    try {
      await streamQuery(
        { question: text, retrieval_only: retrievalOnly, debug: showPrompt },
        {
          onSources: (sources) => update({ sources }),
          onToken: (tok) => update((t) => ({ answer: t.answer + tok })),
          onPrompt: (prompt) => update({ prompt }),
          onError: (message) => update({ error: message, status: 'error' }),
          onDone: () => update((t) => ({ status: t.status === 'error' ? 'error' : 'done', elapsedMs: Date.now() - startedAt })),
        },
        controller.signal,
      )
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') {
        update({ status: 'stopped', elapsedMs: Date.now() - startedAt })
      } else {
        update({ status: 'error', error: e instanceof ApiError ? e.message : 'Something went wrong while asking' })
      }
    } finally {
      abort.current = null
      setBusy(false)
      input.current?.focus()
    }
  }

  function submit(e?: FormEvent) {
    e?.preventDefault()
    const text = question.trim()
    if (!text || busy) return
    setQuestion('')
    void ask(text)
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter adds a line. Ignore Enter while an input method (IME) is composing text.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) submit(e)
  }

  const docCount = docs.data?.length ?? 0

  return (
    <div className="ask">
      <div className="transcript">
        {turns.length === 0 ? (
          <div className="intro">
            <h2>Ask your documents</h2>
            <p>
              Your question is matched against the indexed chunks, the best ones go to the model, and the answer streams in below with
              the sources it used.
            </p>
            {docs.isSuccess && docCount === 0 && (
              <p className="intro__hint">
                No documents were added through this app yet. <Link to="/config">Add some in Settings</Link>, or ask about ones already
                indexed from the command line.
              </p>
            )}
          </div>
        ) : (
          turns.map((t) => <TurnCard key={t.id} turn={t} minScore={settings?.min_score ?? 0} />)
        )}
        <div ref={end} />
      </div>

      <form className="composer" onSubmit={submit}>
        <label htmlFor="question" className="sr-only">Your question</label>
        <textarea
          id="question"
          ref={input}
          rows={2}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask a question about your documents"
          maxLength={2000}
          autoFocus
        />
        <div className="composer__row">
          <label className="check">
            <input type="checkbox" checked={retrievalOnly} onChange={(e) => setRetrievalOnly(e.target.checked)} />
            Retrieval only <span>skip the model</span>
          </label>
          <label className="check">
            <input type="checkbox" checked={showPrompt} onChange={(e) => setShowPrompt(e.target.checked)} />
            Show prompt <span>what the model receives</span>
          </label>
          <span className="composer__spacer" />
          {turns.length > 0 && (
            <button type="button" className="btn btn--quiet" onClick={() => setTurns([])} disabled={busy}>
              Clear
            </button>
          )}
          {busy ? (
            <button type="button" className="btn" onClick={() => abort.current?.abort()}>
              Stop
            </button>
          ) : (
            <button type="submit" className="btn btn--primary" disabled={!question.trim()}>
              Ask
            </button>
          )}
        </div>
        <p className="composer__foot">
          {llm.data ? `Answering with ${modelLabel(llm.data)}` : 'Loading settings'}
          {settings && ` · top ${settings.top_k} chunks · minimum score ${settings.min_score.toFixed(2)}`} ·{' '}
          <Link to="/config">Change in Settings</Link>
          <br />
          Each question stands alone: the model does not see earlier ones. Nothing is saved; refreshing clears this page.
        </p>
      </form>
    </div>
  )
}
