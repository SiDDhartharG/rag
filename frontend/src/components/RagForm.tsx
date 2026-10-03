import { useState, type FormEvent } from 'react'
import { useSaveRag } from '../hooks'
import type { RagSettings, Strategy } from '../types'
import { ChunkRuler } from './ChunkRuler'
import { Field, SaveBar } from './Field'

const STRATEGIES: { value: Strategy; name: string; blurb: string }[] = [
  { value: 'fixed', name: 'Fixed size', blurb: 'Cuts every N tokens with overlap. Fast, ignores meaning.' },
  { value: 'recursive', name: 'Recursive', blurb: 'Splits on paragraphs, then lines, then sentences.' },
  { value: 'sentence', name: 'Sentence', blurb: 'Packs whole sentences up to the size limit.' },
  { value: 'structure', name: 'Structure', blurb: 'Splits at headings and repeats the heading on each piece.' },
  { value: 'semantic', name: 'Semantic', blurb: 'Cuts where the topic shifts. Slower, uneven sizes.' },
]

// Mirrors the backend limits in backend/app/schemas.py. The server is still the source of truth.
function validate(s: RagSettings): string[] {
  const problems: string[] = []
  if (!(s.chunk_tokens >= 20 && s.chunk_tokens <= 250)) problems.push('Chunk size must be between 20 and 250 tokens')
  if (s.overlap < 0 || s.overlap >= s.chunk_tokens) problems.push('Overlap must be at least 0 and smaller than the chunk size')
  if (!(s.top_k >= 1 && s.top_k <= 20)) problems.push('Chunks sent to the model must be between 1 and 20')
  if (!(s.min_score >= 0 && s.min_score <= 1)) problems.push('Minimum score must be between 0 and 1')
  return problems
}

export function RagForm({ server }: { server: RagSettings }) {
  const [draft, setDraft] = useState<RagSettings>(server)
  const save = useSaveRag()
  const dirty = JSON.stringify(draft) !== JSON.stringify(server)
  const problems = validate(draft)
  const set = <K extends keyof RagSettings>(key: K, value: RagSettings[K]) => setDraft({ ...draft, [key]: value })
  const num = (v: string) => (v === '' ? NaN : Number(v))

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate(draft)
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <header className="panel__head">
        <span className="eyebrow">Chunk</span>
        <h2>Chunking</h2>
        <p>How documents are cut up before they are indexed. Changing these means re-indexing.</p>
      </header>

      <fieldset className="strategies">
        <legend>Strategy</legend>
        {STRATEGIES.map((s) => (
          <label key={s.value} className={`strategy${draft.strategy === s.value ? ' strategy--on' : ''}`}>
            <input
              type="radio"
              name="strategy"
              value={s.value}
              checked={draft.strategy === s.value}
              onChange={() => set('strategy', s.value)}
            />
            <span className="strategy__name">{s.name}</span>
            <span className="strategy__blurb">{s.blurb}</span>
          </label>
        ))}
      </fieldset>

      <Field id="chunk_tokens" label="Chunk size" readout={`${draft.chunk_tokens} tokens`} hint="Limit is 250: the embedding model ignores anything past 256 tokens.">
        <div className="pair">
          <input type="range" min={20} max={250} step={10} value={Number.isNaN(draft.chunk_tokens) ? 20 : draft.chunk_tokens} onChange={(e) => set('chunk_tokens', num(e.target.value))} aria-label="Chunk size slider" />
          <input id="chunk_tokens" type="number" min={20} max={250} value={Number.isNaN(draft.chunk_tokens) ? '' : draft.chunk_tokens} onChange={(e) => set('chunk_tokens', num(e.target.value))} />
        </div>
      </Field>

      <Field id="overlap" label="Overlap" readout={`${draft.overlap} tokens`} hint={draft.strategy === 'fixed' ? 'Tokens repeated between neighbouring chunks.' : 'Only the fixed size strategy uses overlap.'}>
        <div className="pair">
          <input type="range" min={0} max={Math.max(0, draft.chunk_tokens - 1)} step={5} disabled={draft.strategy !== 'fixed'} value={Number.isNaN(draft.overlap) ? 0 : draft.overlap} onChange={(e) => set('overlap', num(e.target.value))} aria-label="Overlap slider" />
          <input id="overlap" type="number" min={0} disabled={draft.strategy !== 'fixed'} value={Number.isNaN(draft.overlap) ? '' : draft.overlap} onChange={(e) => set('overlap', num(e.target.value))} />
        </div>
      </Field>

      <ChunkRuler chunkTokens={draft.chunk_tokens} overlap={draft.overlap} strategy={draft.strategy} />

      <header className="panel__head panel__head--sub">
        <span className="eyebrow">Search</span>
        <h2>Retrieval</h2>
        <p>Which chunks reach the model. These apply to the next question; no re-index needed.</p>
      </header>

      <Field id="top_k" label="Chunks sent to the model" readout={String(draft.top_k)} hint="More context can help, but also adds noise and cost.">
        <div className="pair">
          <input type="range" min={1} max={20} value={Number.isNaN(draft.top_k) ? 1 : draft.top_k} onChange={(e) => set('top_k', num(e.target.value))} aria-label="Chunks sent to the model slider" />
          <input id="top_k" type="number" min={1} max={20} value={Number.isNaN(draft.top_k) ? '' : draft.top_k} onChange={(e) => set('top_k', num(e.target.value))} />
        </div>
      </Field>

      <Field id="min_score" label="Minimum match score" readout={Number.isNaN(draft.min_score) ? '' : draft.min_score.toFixed(2)} hint="Chunks scoring below this are dropped. If none are left, the model is not called and the answer is “I don’t know”.">
        <div className="pair">
          <input type="range" min={0} max={1} step={0.01} value={Number.isNaN(draft.min_score) ? 0 : draft.min_score} onChange={(e) => set('min_score', num(e.target.value))} aria-label="Minimum match score slider" />
          <input id="min_score" type="number" min={0} max={1} step={0.01} value={Number.isNaN(draft.min_score) ? '' : draft.min_score} onChange={(e) => set('min_score', num(e.target.value))} />
        </div>
      </Field>

      <SaveBar dirty={dirty} problems={dirty ? problems : []} saving={save.isPending} saved={save.isSuccess} error={save.error} onDiscard={() => { setDraft(server); save.reset() }} />
    </form>
  )
}
