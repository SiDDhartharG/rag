import json
import os
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Protocol

from rag.config import LLMConfig


class LLMClient(Protocol):
    def stream(self, system: str, user: str) -> Iterator[str]:
        """Yield the answer in text pieces as the model produces them."""


class ClaudeLLM:
    def __init__(self, cfg):
        if not (os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")):
            raise RuntimeError("No Anthropic credentials: put ANTHROPIC_API_KEY=... in .env (or use provider = 'ollama')")
        import anthropic

        self.cfg = cfg
        self.client = anthropic.Anthropic()

    def stream(self, system: str, user: str) -> Iterator[str]:
        with self.client.messages.stream(
            model=self.cfg.model,
            max_tokens=self.cfg.max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": self.cfg.effort},
        ) as stream:
            yield from stream.text_stream
            final = stream.get_final_message()
        if final.stop_reason == "refusal":
            yield "\n[The model declined to answer this request.]"
        elif final.stop_reason == "max_tokens":
            yield "\n[Answer cut off: raise llm.claude.max_tokens]"


class OllamaLLM:
    def __init__(self, cfg):
        self.cfg = cfg

    def stream(self, system: str, user: str) -> Iterator[str]:
        body = json.dumps({
            "model": self.cfg.model,
            "stream": True,
            "options": {"temperature": self.cfg.temperature},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }).encode()
        req = urllib.request.Request(
            f"{self.cfg.host}/api/chat", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                for line in resp:  # one JSON object per line
                    chunk = json.loads(line)
                    if "error" in chunk:
                        raise RuntimeError(f"Ollama error: {chunk['error']} (try: ollama pull {self.cfg.model})")
                    yield chunk.get("message", {}).get("content", "")
                    if chunk.get("done"):
                        return
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.cfg.host} ({e.reason}). Start it with `ollama serve` "
                f"and pull the model with `ollama pull {self.cfg.model}`."
            ) from e


class EchoLLM:
    """Offline test provider: no model, just proves retrieval + prompt building work."""

    def stream(self, system: str, user: str) -> Iterator[str]:
        yield f"[echo provider, no model called] prompt was {len(system) + len(user)} characters"


def get_llm(cfg: LLMConfig) -> LLMClient:
    """Pick the provider named in config. To add one, write a class with .stream() and register it."""
    if cfg.provider == "claude":
        return ClaudeLLM(cfg.claude)
    if cfg.provider == "ollama":
        return OllamaLLM(cfg.ollama)
    if cfg.provider == "echo":
        return EchoLLM()
    raise ValueError(f"Unknown llm.provider {cfg.provider!r}; choose claude | ollama | echo")
