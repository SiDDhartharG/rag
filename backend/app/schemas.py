"""Request/response shapes and validation for the API.

These mirror the dataclasses in rag/config.py. Pydantic validates user input here, so bad values
(e.g. chunk_tokens=5000) are rejected with a 422 before they can reach the RAG code. API keys are
deliberately NOT part of any schema: they live in .env on the server and never pass through the API.
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

from rag.config import ClaudeConfig, LLMConfig, OllamaConfig, RagConfig, RetrievalConfig
from rag.pipeline import IngestConfig


class RagSettings(BaseModel):
    strategy: Literal["fixed", "recursive", "sentence", "structure", "semantic"] = "structure"
    # The embedding model (MiniLM) silently truncates input at 256 tokens, so cap chunk size below that.
    chunk_tokens: int = Field(200, ge=20, le=250)
    overlap: int = Field(40, ge=0)  # only used by "fixed"
    top_k: int = Field(4, ge=1, le=20)
    min_score: float = Field(0.15, ge=0, le=1)

    @model_validator(mode="after")
    def overlap_smaller_than_chunk(self) -> Self:
        if self.overlap >= self.chunk_tokens:
            raise ValueError("overlap must be smaller than chunk_tokens")
        return self


class ClaudeSettings(BaseModel):
    model: str = Field("claude-opus-5-5", min_length=1)
    max_tokens: int = Field(2048, ge=1, le=64000)
    effort: Literal["", "low", "medium", "high", "xhigh", "max"] = "low"  # "" = omit


class OllamaSettings(BaseModel):
    model: str = Field("llama3.2", min_length=1)
    host: str = Field("http://localhost:11434", pattern=r"^https?://")
    temperature: float = Field(0.2, ge=0, le=2)


class LLMSettings(BaseModel):
    provider: Literal["ollama", "claude", "echo"] = "ollama"
    system_prompt: str = Field(min_length=1)
    claude: ClaudeSettings = ClaudeSettings()
    ollama: OllamaSettings = OllamaSettings()


class RagConfigResponse(BaseModel):
    settings: RagSettings
    # True when a setting that changes the stored vectors (strategy, chunk size, overlap) was edited
    # after documents were indexed. Click "Re-index" to apply it to existing documents.
    needs_reindex: bool


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    retrieval_only: bool = False  # skip the LLM, return just the matching chunks
    debug: bool = False  # also stream the exact prompt the LLM received


class DocumentOut(BaseModel):
    id: int
    filename: str
    status: Literal["pending", "indexing", "ready", "failed"]
    chunks: int
    error: str | None


def to_rag_config(rag: RagSettings, llm: LLMSettings, collection: str) -> RagConfig:
    """Convert validated API settings into the dataclasses the rag/ package expects."""
    return RagConfig(
        ingest=IngestConfig(
            strategy=rag.strategy, chunk_tokens=rag.chunk_tokens, overlap=rag.overlap, collection=collection
        ),
        retrieval=RetrievalConfig(top_k=rag.top_k, min_score=rag.min_score),
        llm=LLMConfig(
            provider=llm.provider,
            system_prompt=llm.system_prompt,
            claude=ClaudeConfig(**llm.claude.model_dump()),
            ollama=OllamaConfig(**llm.ollama.model_dump()),
        ),
    )
