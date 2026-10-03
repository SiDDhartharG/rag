import { useRef, useState, type DragEvent } from 'react'
import { ApiError } from '../api'
import { useDeleteDoc, useDocuments, useUpload } from '../hooks'
import type { DocStatus } from '../types'

const STATUS_TEXT: Record<DocStatus, string> = {
  pending: 'Waiting',
  indexing: 'Indexing',
  ready: 'Ready',
  failed: 'Failed',
}

export function Documents() {
  const docs = useDocuments()
  const upload = useUpload()
  const remove = useDeleteDoc()
  const input = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [errors, setErrors] = useState<string[]>([])

  async function addFiles(files: FileList | File[]) {
    const problems: string[] = []
    for (const file of Array.from(files)) {
      try {
        await upload.mutateAsync(file)
      } catch (e) {
        problems.push(`${file.name}: ${e instanceof ApiError ? e.message : 'upload failed'}`)
      }
    }
    setErrors(problems)
  }

  const onDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files.length) void addFiles(e.dataTransfer.files)
  }

  const list = docs.data ?? []

  return (
    <section
      className={`panel docs${dragging ? ' docs--drag' : ''}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      aria-labelledby="docs-title"
    >
      <header className="panel__head panel__head--row">
        <div>
          <span className="eyebrow">Load</span>
          <h2 id="docs-title">Documents</h2>
          <p>PDF, text or markdown, up to 20 MB each. Drop files anywhere on this panel.</p>
        </div>
        <button type="button" className="btn btn--primary" onClick={() => input.current?.click()} disabled={upload.isPending}>
          {upload.isPending ? 'Uploading…' : 'Add documents'}
        </button>
        <input
          ref={input}
          type="file"
          multiple
          accept=".pdf,.txt,.md"
          hidden
          onChange={(e) => {
            if (e.target.files?.length) void addFiles(e.target.files)
            e.target.value = '' // allow choosing the same file again
          }}
        />
      </header>

      {errors.map((m) => (
        <p key={m} className="savebar__error" role="alert">{m}</p>
      ))}

      {docs.isError && <p className="savebar__error" role="alert">Could not load documents.</p>}

      {!docs.isError && list.length === 0 && !docs.isLoading && (
        <p className="empty">No documents yet. Add a file to index it, then ask questions about it.</p>
      )}

      {list.length > 0 && (
        <ul className="doclist">
          {list.map((d) => (
            <li key={d.id} className="doc">
              <span className="doc__name" title={d.filename}>{d.filename}</span>
              <span className={`pill pill--${d.status}`}>{STATUS_TEXT[d.status]}</span>
              <span className="doc__chunks">{d.status === 'ready' ? `${d.chunks} chunks` : ''}</span>
              <button
                type="button"
                className="btn btn--quiet"
                disabled={d.status === 'indexing' || remove.isPending}
                onClick={() => {
                  if (window.confirm(`Delete ${d.filename}? Its indexed chunks are removed too.`)) remove.mutate(d.id)
                }}
                aria-label={`Delete ${d.filename}`}
              >
                Delete
              </button>
              {d.error && <p className="doc__error">{d.error}</p>}
            </li>
          ))}
        </ul>
      )}

      <p className="note">Documents indexed from the command line are searched too, but only files added here are listed.</p>
    </section>
  )
}
