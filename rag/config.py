import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from rag.pipeline import IngestConfig

DEFAULT_CONFIG_PATH = Path("config.toml")


@dataclass
class RetrievalConfig:
    top_k: int = 4
    min_score: float = 0.15


@dataclass
class ClaudeConfig:
    model: str = "claude-opus-5-5"
    max_tokens: int = 2048
    effort: str = "low"


@dataclass
class OllamaConfig:
    model: str = "llama3.2"
    host: str = "http://localhost:11434"
    temperature: float = 0.2


@dataclass
class LLMConfig:
    provider: str = "claude"
    system_prompt: str = "Answer using only the numbered context. Cite passages like [1]."
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)


@dataclass
class RagConfig:
    ingest: IngestConfig = field(default_factory=IngestConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)


def _build(cls, values: dict, where: str):
    try:
        return cls(**values)
    except TypeError as e:
        raise ValueError(f"Bad config in [{where}]: {e}") from e


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> RagConfig:
    """Read config.toml (missing keys fall back to defaults; unknown keys are an error)."""
    load_dotenv()  # puts ANTHROPIC_API_KEY from .env into the environment
    raw = tomllib.loads(path.read_text()) if path.exists() else {}
    llm_raw = dict(raw.get("llm", {}))
    claude = _build(ClaudeConfig, llm_raw.pop("claude", {}), "llm.claude")
    ollama = _build(OllamaConfig, llm_raw.pop("ollama", {}), "llm.ollama")
    return RagConfig(
        ingest=_build(IngestConfig, raw.get("ingest", {}), "ingest"),
        retrieval=_build(RetrievalConfig, raw.get("retrieval", {}), "retrieval"),
        llm=_build(LLMConfig, {**llm_raw, "claude": claude, "ollama": ollama}, "llm"),
    )
