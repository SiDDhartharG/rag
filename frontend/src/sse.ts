import { API_BASE, ApiError, readableErrors } from './api'
import type { PromptParts, QueryRequest, Source } from './types'

export interface QueryHandlers {
  onSources: (sources: Source[]) => void
  onToken: (text: string) => void
  onPrompt: (prompt: PromptParts) => void
  onError: (message: string) => void
  onDone: () => void
}

/** One Server-Sent Event block looks like "event: token\ndata: \"hi\"". */
function dispatch(block: string, h: QueryHandlers) {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7)
    else if (line.startsWith('data: ')) data += line.slice(6)
  }
  if (!data) return
  const payload = JSON.parse(data)
  if (event === 'sources') h.onSources(payload)
  else if (event === 'token') h.onToken(payload)
  else if (event === 'prompt') h.onPrompt(payload)
  else if (event === 'error') h.onError(payload)
  else if (event === 'done') h.onDone()
}

/**
 * POST /query and read the event stream. The browser's EventSource only supports GET, so we read the
 * response body ourselves. Pass an AbortSignal to stop; that rejects with an AbortError.
 */
export async function streamQuery(req: QueryRequest, h: QueryHandlers, signal: AbortSignal): Promise<void> {
  let res: Response
  try {
    res = await fetch(`${API_BASE}/query`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(req),
      signal,
    })
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e
    throw new ApiError(0, [`Cannot reach the API at ${API_BASE}. Is the backend running?`])
  }
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, readableErrors(body.detail))
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let end: number
    while ((end = buffer.indexOf('\n\n')) >= 0) {
      dispatch(buffer.slice(0, end), h)
      buffer = buffer.slice(end + 2)
    }
  }
}
