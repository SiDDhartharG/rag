"""Config-driven RAG: the same question run through different providers just by changing config."""
import dataclasses
import inspect

import anthropic

from rag.config import load_config
from rag.generation import answer

cfg = load_config()
print("Loaded config.toml:")
print(f"  ingest    {cfg.ingest}")
print(f"  retrieval {cfg.retrieval}")
print(f"  provider  {cfg.llm.provider}  claude={cfg.llm.claude}  ollama={cfg.llm.ollama}")

print("\n" + "=" * 70 + "\n1. Answerable question, echo provider (no model): proves retrieval + prompt + wiring\n" + "=" * 70)
cfg.llm.provider = "echo"
r = answer("What programming languages and tools does he know?", cfg)
print(r.text)
print("sources:", [(round(h['score'], 2), h['metadata']['chunk_index']) for h in r.sources])

print("\n" + "=" * 70 + "\n2. Off-topic question: below min_score => LLM is never called\n" + "=" * 70)
r = answer("How do I bake sourdough bread?", cfg)
print(r.text, "| sources:", r.sources)

print("\n" + "=" * 70 + "\n3. Raising min_score in config changes what survives\n" + "=" * 70)
for ms in (0.0, 0.15, 0.4):
    cfg.retrieval.min_score = ms
    n = len(answer("Where did he study?", cfg).sources)
    print(f"  min_score={ms}: {n} chunk(s) kept")
cfg.retrieval.min_score = 0.15

print("\n" + "=" * 70 + "\n4. Switching provider = one config value. Real backends, with their setup errors:\n" + "=" * 70)
for provider in ("claude", "ollama"):
    cfg.llm.provider = provider
    try:
        print(f"  {provider}: {answer('Where did he study?', cfg).text[:200]}")
    except RuntimeError as e:
        print(f"  {provider}: {e}")

print("\n" + "=" * 70 + "\n5. Does the installed SDK accept the params we send to Claude?\n" + "=" * 70)
params = inspect.signature(anthropic.Anthropic.messages.__get__ if False else anthropic.resources.messages.Messages.stream).parameters
print("  anthropic", anthropic.__version__, "| stream() accepts output_config:", "output_config" in params,
      "| system:", "system" in params)

print("\nBad provider name:")
cfg.llm.provider = "gpt"
try:
    answer("Where did he study?", cfg)
except ValueError as e:
    print(" ", e)
