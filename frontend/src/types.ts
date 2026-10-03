// These mirror the Pydantic models in backend/app/schemas.py.

export type Strategy = 'fixed' | 'recursive' | 'sentence' | 'structure' | 'semantic'

export interface RagSettings {
  strategy: Strategy
  chunk_tokens: number
  overlap: number
  top_k: number
  min_score: number
}

export interface RagConfigResponse {
  settings: RagSettings
  needs_reindex: boolean
}

export type Provider = 'ollama' | 'claude' | 'echo'
export type Effort = '' | 'low' | 'medium' | 'high' | 'xhigh' | 'max'

export interface ClaudeSettings {
  model: string
  max_tokens: number
  effort: Effort
}

export interface OllamaSettings {
  model: string
  host: string
  temperature: number
}

export interface LLMSettings {
  provider: Provider
  system_prompt: string
  claude: ClaudeSettings
  ollama: OllamaSettings
}

export type DocStatus = 'pending' | 'indexing' | 'ready' | 'failed'

export interface DocumentOut {
  id: number
  filename: string
  status: DocStatus
  chunks: number
  error: string | null
}

export interface Source {
  score: number
  source: string
  chunk_index: number
  text: string
}

export interface QueryRequest {
  question: string
  retrieval_only: boolean
  debug: boolean
}

export interface PromptParts {
  system: string
  user: string
}
