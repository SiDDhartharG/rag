import type { DocumentOut, LLMSettings, RagConfigResponse, RagSettings } from './types'

export const API_BASE: string = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000'

/** An API failure with messages already readable by a person. */
export class ApiError extends Error {
  status: number
  messages: string[]

  constructor(status: number, messages: string[]) {
    super(messages.join('; '))
    this.status = status
    this.messages = messages
  }
}

/** FastAPI sends {detail: "text"} for HTTP errors and {detail: [{loc, msg}]} for validation errors. */
export function readableErrors(detail: unknown): string[] {
  if (typeof detail === 'string') return [detail]
  if (Array.isArray(detail)) {
    return detail.map((d: { loc?: (string | number)[]; msg?: string }) => {
      const field = d.loc?.filter((p) => p !== 'body').join('.')
      return field ? `${field}: ${d.msg}` : String(d.msg)
    })
  }
  return ['Unexpected error from the server']
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, init)
  } catch {
    throw new ApiError(0, [`Cannot reach the API at ${API_BASE}. Is the backend running?`])
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, readableErrors(body.detail))
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
})

export const api = {
  health: () => request<{ status: string }>('/health'),
  getRag: () => request<RagConfigResponse>('/config/rag'),
  putRag: (s: RagSettings) => request<RagConfigResponse>('/config/rag', json('PUT', s)),
  getLlm: () => request<LLMSettings>('/config/llm'),
  putLlm: (s: LLMSettings) => request<LLMSettings>('/config/llm', json('PUT', s)),
  listDocs: () => request<DocumentOut[]>('/documents'),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<DocumentOut>('/documents', { method: 'POST', body: form })
  },
  deleteDoc: (id: number) => request<void>(`/documents/${id}`, { method: 'DELETE' }),
  reindex: () => request<{ queued: number }>('/reindex', { method: 'POST' }),
}
