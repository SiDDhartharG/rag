import { useState } from 'react'
import type { PromptParts, Source } from '../types'

export interface Turn {
  id: number
  question: string
  answer: string
  sources: Source[] | null // null until the first event arrives
  prompt: PromptParts | null
  error: string | null
  status: 'streaming' | 'done' | 'stopped' | 'error'
  retrievalOnly: boolean
  by: string // which model answered, recorded when the question was asked
  startedAt: number
  elapsedMs: number | null
}

/** Turns "see [1] and [2]" into text plus buttons that jump to the matching source. */
function Answer({ text, sourceCount, onCite }: { text: string; sourceCount: number; onCite: (n: number) => void }) {
  return (
    <p className="answer">
      {text.split(/(\[\d+\])/).map((part, i) => {
        const m = /^\[(\d+)\]$/.exec(part)
        const n = m ? Number(m[1]) : 0
        return m && n >= 1 && n <= sourceCount ? (
          <button key={i} type="button" className="cite" onClick={() => onCite(n)} aria-label={`Show source ${n}`}>
            {part}
          </button>
        ) : (
          part
        )
      })}
    </p>
  )
}

function SourceRow({ n, s, minScore, turnId, open, onToggle }: {
  n: number
  s: Source
  minScore: number
  turnId: number
  open: boolean
  onToggle: (open: boolean) => void
}) {
  return (
    <details id={`src-${turnId}-${n}`} className="source" open={open} onToggle={(e) => onToggle(e.currentTarget.open)}>
      <summary className="source__summary">
        <span className="source__n">[{n}]</span>
        <span className="source__file" title={`${s.source}, chunk ${s.chunk_index}`}>
          {s.source}
          <span className="source__chunk"> #{s.chunk_index}</span>
        </span>
        <span className="source__bar" role="img" aria-label={`Match score ${s.score.toFixed(2)}, cutoff ${minScore.toFixed(2)}`}>
          <span className="source__fill" style={{ width: `${Math.min(100, s.score * 100)}%` }} />
          <span className="source__cutoff" style={{ left: `${minScore * 100}%` }} />
        </span>
        <span className="source__score">{s.score.toFixed(2)}</span>
      </summary>
      <pre className="source__text">{s.text}</pre>
    </details>
  )
}

export function TurnCard({ turn, minScore }: { turn: Turn; minScore: number }) {
  const [openSources, setOpenSources] = useState<Set<number>>(new Set())
  const sources = turn.sources ?? []
  const noMatch = turn.status === 'done' && turn.sources !== null && sources.length === 0

  const cite = (n: number) => {
    setOpenSources((prev) => new Set(prev).add(n))
    // Wait a frame so the <details> has opened before scrolling to it.
    requestAnimationFrame(() => document.getElementById(`src-${turn.id}-${n}`)?.scrollIntoView({ block: 'nearest' }))
  }

  const setOpen = (n: number, open: boolean) =>
    setOpenSources((prev) => {
      const next = new Set(prev)
      if (open) next.add(n)
      else next.delete(n)
      return next
    })

  return (
    <article className="turn" aria-label={`Question: ${turn.question}`}>
      <h2 className="turn__q">{turn.question}</h2>

      {turn.retrievalOnly ? (
        <p className="turn__mode">Retrieval only: the model was not called. These are the chunks the search found.</p>
      ) : (
        (turn.answer || turn.status === 'streaming') && (
          <div className="turn__a" aria-live={turn.status === 'streaming' ? 'off' : 'polite'}>
            <Answer text={turn.answer} sourceCount={sources.length} onCite={cite} />
            {turn.status === 'streaming' && !turn.answer && <p className="waiting">Searching your documents…</p>}
            {turn.status === 'streaming' && turn.answer && <span className="caret" aria-hidden="true" />}
          </div>
        )
      )}

      {noMatch && !turn.retrievalOnly && (
        <p className="turn__note">
          No chunk scored at least {minScore.toFixed(2)}, so the model was not called. Lower the minimum match score in Settings, or
          rephrase the question.
        </p>
      )}
      {noMatch && turn.retrievalOnly && <p className="turn__note">No chunk scored at least {minScore.toFixed(2)}.</p>}

      {turn.error && (
        <p className="turn__error" role="alert">
          {turn.error}
        </p>
      )}
      {turn.status === 'stopped' && <p className="turn__note">Stopped.</p>}

      {sources.length > 0 && (
        <section className="sources" aria-label="Sources">
          <h3>
            Sources <span>chunks scoring at least {minScore.toFixed(2)}; the tick marks that cutoff</span>
          </h3>
          {sources.map((s, i) => (
            <SourceRow
              key={i}
              n={i + 1}
              s={s}
              minScore={minScore}
              turnId={turn.id}
              open={openSources.has(i + 1)}
              onToggle={(open) => setOpen(i + 1, open)}
            />
          ))}
        </section>
      )}

      {turn.prompt && (
        <details className="promptview">
          <summary>{turn.retrievalOnly ? 'Prompt that would be sent to the model' : 'Prompt sent to the model'}</summary>
          <h4>Instructions</h4>
          <pre>{turn.prompt.system}</pre>
          <h4>Context and question</h4>
          <pre>{turn.prompt.user}</pre>
        </details>
      )}

      <p className="turn__meta">
        {turn.retrievalOnly ? 'retrieval only' : noMatch ? 'model not called' : turn.by}
        {turn.elapsedMs !== null && ` · ${(turn.elapsedMs / 1000).toFixed(1)} s`}
        {turn.status === 'streaming' && ' · working'}
      </p>
    </article>
  )
}
