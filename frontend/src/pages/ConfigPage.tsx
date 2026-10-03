import { ApiError } from '../api'
import { Documents } from '../components/Documents'
import { LlmForm } from '../components/LlmForm'
import { RagForm } from '../components/RagForm'
import { useDocuments, useLlmConfig, useRagConfig, useReindex } from '../hooks'

function ReindexBanner() {
  const rag = useRagConfig()
  const docs = useDocuments()
  const reindex = useReindex()
  const count = docs.data?.length ?? 0
  if (!rag.data?.needs_reindex) return null
  return (
    <div className="banner" role="status">
      <p>
        <strong>Chunking settings changed.</strong> Your {count} indexed {count === 1 ? 'document was' : 'documents were'} cut with the old
        settings. Re-index to apply the new ones.
      </p>
      <button type="button" className="btn btn--primary" onClick={() => reindex.mutate()} disabled={reindex.isPending}>
        {reindex.isPending ? 'Starting…' : `Re-index ${count} ${count === 1 ? 'document' : 'documents'}`}
      </button>
      {reindex.error instanceof ApiError && <p className="savebar__error" role="alert">{reindex.error.message}</p>}
    </div>
  )
}

export default function ConfigPage() {
  const rag = useRagConfig()
  const llm = useLlmConfig()
  return (
    <>
      <ReindexBanner />
      <Documents />
      <div className="cols">
        {rag.data ? (
          // The key makes the form restart from the server's values after a save or a re-index.
          <RagForm key={JSON.stringify(rag.data.settings)} server={rag.data.settings} />
        ) : (
          <div className="panel skeleton">{rag.isError ? 'Could not load chunking settings.' : 'Loading chunking settings…'}</div>
        )}
        {llm.data ? (
          <LlmForm key={JSON.stringify(llm.data)} server={llm.data} />
        ) : (
          <div className="panel skeleton">{llm.isError ? 'Could not load model settings.' : 'Loading model settings…'}</div>
        )}
      </div>
    </>
  )
}
