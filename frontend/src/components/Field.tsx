import type { ReactNode } from 'react'
import { ApiError } from '../api'

interface FieldProps {
  id: string
  label: string
  hint?: string
  readout?: string
  children: ReactNode
}

/** A labelled control with an optional hint underneath and a monospace readout of its value. */
export function Field({ id, label, hint, readout, children }: FieldProps) {
  return (
    <div className="field">
      <div className="field__row">
        <label htmlFor={id}>{label}</label>
        {readout !== undefined && <output className="field__readout">{readout}</output>}
      </div>
      {children}
      {hint && <p className="field__hint">{hint}</p>}
    </div>
  )
}

interface SaveBarProps {
  dirty: boolean
  problems: string[]
  saving: boolean
  saved: boolean
  error: unknown
  onDiscard: () => void
}

/** Save/discard buttons plus any client-side problems or server errors. */
export function SaveBar({ dirty, problems, saving, saved, error, onDiscard }: SaveBarProps) {
  const serverMessages = error instanceof ApiError ? error.messages : error ? ['Could not save settings'] : []
  return (
    <div className="savebar">
      {[...problems, ...serverMessages].map((m) => (
        <p key={m} className="savebar__error" role="alert">
          {m}
        </p>
      ))}
      <div className="savebar__actions">
        <button type="submit" className="btn btn--primary" disabled={!dirty || problems.length > 0 || saving}>
          {saving ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className="btn" disabled={!dirty || saving} onClick={onDiscard}>
          Discard
        </button>
        <span className="savebar__status" aria-live="polite">
          {saved && !dirty ? 'Saved' : dirty ? 'Unsaved changes' : ''}
        </span>
      </div>
    </div>
  )
}
