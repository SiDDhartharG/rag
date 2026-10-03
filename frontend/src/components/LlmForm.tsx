import { useState, type FormEvent } from 'react'
import { useSaveLlm } from '../hooks'
import type { Effort, LLMSettings, Provider } from '../types'
import { Field, SaveBar } from './Field'

const PROVIDERS: { value: Provider; name: string; blurb: string }[] = [
  { value: 'ollama', name: 'Ollama', blurb: 'Runs on this machine. Free.' },
  { value: 'claude', name: 'Claude', blurb: 'Anthropic API. Needs a key on the server.' },
  { value: 'echo', name: 'Echo', blurb: 'No model. Tests the wiring only.' },
]

const EFFORTS: { value: Effort; label: string }[] = [
  { value: '', label: 'Not set (for models without effort)' },
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
  { value: 'xhigh', label: 'Extra high' },
  { value: 'max', label: 'Max' },
]

function validate(s: LLMSettings): string[] {
  const problems: string[] = []
  if (!s.system_prompt.trim()) problems.push('Instructions cannot be empty')
  if (s.provider === 'ollama') {
    if (!s.ollama.model.trim()) problems.push('Ollama model name is required')
    if (!/^https?:\/\//.test(s.ollama.host)) problems.push('Ollama address must start with http:// or https://')
    if (!(s.ollama.temperature >= 0 && s.ollama.temperature <= 2)) problems.push('Temperature must be between 0 and 2')
  }
  if (s.provider === 'claude') {
    if (!s.claude.model.trim()) problems.push('Claude model name is required')
    if (!(s.claude.max_tokens >= 1 && s.claude.max_tokens <= 64000)) problems.push('Max answer length must be between 1 and 64,000 tokens')
  }
  return problems
}

export function LlmForm({ server }: { server: LLMSettings }) {
  const [draft, setDraft] = useState<LLMSettings>(server)
  const save = useSaveLlm()
  const dirty = JSON.stringify(draft) !== JSON.stringify(server)
  const problems = validate(draft)
  const num = (v: string) => (v === '' ? NaN : Number(v))

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    save.mutate(draft)
  }

  return (
    <form className="panel" onSubmit={onSubmit}>
      <header className="panel__head">
        <span className="eyebrow">Answer</span>
        <h2>Model</h2>
        <p>Which model writes the answer from the retrieved chunks. Applies to the next question.</p>
      </header>

      <fieldset className="strategies">
        <legend>Provider</legend>
        {PROVIDERS.map((p) => (
          <label key={p.value} className={`strategy${draft.provider === p.value ? ' strategy--on' : ''}`}>
            <input type="radio" name="provider" value={p.value} checked={draft.provider === p.value} onChange={() => setDraft({ ...draft, provider: p.value })} />
            <span className="strategy__name">{p.name}</span>
            <span className="strategy__blurb">{p.blurb}</span>
          </label>
        ))}
      </fieldset>

      {draft.provider === 'ollama' && (
        <>
          <Field id="ollama_model" label="Model" hint="Must already be pulled: ollama pull <name>.">
            <input id="ollama_model" type="text" className="text" value={draft.ollama.model} onChange={(e) => setDraft({ ...draft, ollama: { ...draft.ollama, model: e.target.value } })} />
          </Field>
          <Field id="ollama_host" label="Server address">
            <input id="ollama_host" type="text" className="text" value={draft.ollama.host} onChange={(e) => setDraft({ ...draft, ollama: { ...draft.ollama, host: e.target.value } })} />
          </Field>
          <Field id="ollama_temp" label="Temperature" readout={Number.isNaN(draft.ollama.temperature) ? '' : draft.ollama.temperature.toFixed(1)} hint="Lower is steadier. Higher varies the wording more.">
            <div className="pair">
              <input type="range" min={0} max={2} step={0.1} value={Number.isNaN(draft.ollama.temperature) ? 0 : draft.ollama.temperature} onChange={(e) => setDraft({ ...draft, ollama: { ...draft.ollama, temperature: num(e.target.value) } })} aria-label="Temperature slider" />
              <input id="ollama_temp" type="number" min={0} max={2} step={0.1} value={Number.isNaN(draft.ollama.temperature) ? '' : draft.ollama.temperature} onChange={(e) => setDraft({ ...draft, ollama: { ...draft.ollama, temperature: num(e.target.value) } })} />
            </div>
          </Field>
        </>
      )}

      {draft.provider === 'claude' && (
        <>
          <Field id="claude_model" label="Model">
            <input id="claude_model" type="text" className="text" value={draft.claude.model} onChange={(e) => setDraft({ ...draft, claude: { ...draft.claude, model: e.target.value } })} />
          </Field>
          <Field id="claude_effort" label="Effort" hint="How much thinking the model does. Some models, such as Haiku 4.5, reject this setting: choose “Not set”.">
            <select id="claude_effort" value={draft.claude.effort} onChange={(e) => setDraft({ ...draft, claude: { ...draft.claude, effort: e.target.value as Effort } })}>
              {EFFORTS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </Field>
          <Field id="claude_max" label="Max answer length" readout={Number.isNaN(draft.claude.max_tokens) ? '' : `${draft.claude.max_tokens} tokens`}>
            <input id="claude_max" type="number" className="text" min={1} max={64000} value={Number.isNaN(draft.claude.max_tokens) ? '' : draft.claude.max_tokens} onChange={(e) => setDraft({ ...draft, claude: { ...draft.claude, max_tokens: num(e.target.value) } })} />
          </Field>
          <p className="note">The API key is read from <code>ANTHROPIC_API_KEY</code> in the server’s <code>.env</code> file. It never passes through this page.</p>
        </>
      )}

      {draft.provider === 'echo' && <p className="note">Echo calls no model. Use it to check that retrieval and the prompt work.</p>}

      <Field id="system_prompt" label="Instructions to the model" hint="Sent with every question. Retrieved chunks are added below it, numbered [1], [2], and so on.">
        <textarea id="system_prompt" rows={6} value={draft.system_prompt} onChange={(e) => setDraft({ ...draft, system_prompt: e.target.value })} />
      </Field>

      <SaveBar dirty={dirty} problems={dirty ? problems : []} saving={save.isPending} saved={save.isSuccess} error={save.error} onDiscard={() => { setDraft(server); save.reset() }} />
    </form>
  )
}
