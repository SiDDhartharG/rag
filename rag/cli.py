"""Command-line entry point for the RAG system.

Usage:
  uv run python -m rag.cli ingest [path]
  uv run python -m rag.cli ask "question" [--provider ollama|claude|echo] [--show-prompt] [--retrieval-only]

Every step prints a "[step]" line so you can see what the pipeline is doing:
  ingest: load -> chunk -> embed -> store
  ask:    embed question -> search vector DB -> filter by min_score -> build prompt -> LLM answer
"""

import argparse
import sys
from pathlib import Path

from rag.config import load_config
from rag.generation import answer, build_prompt, retrieve
from rag.pipeline import ingest


def step(msg: str) -> None:
    """Print a progress line. Kept separate so the format is changed in one place."""
    print(f"[step] {msg}")


def print_sources(hits: list[dict]) -> None:
    """One line per retrieved chunk: rank, similarity score (0-1), source file and chunk number."""
    for i, h in enumerate(hits, 1):
        print(f"  [{i}] score={h['score']:.2f} {h['metadata']['source']}#{h['metadata']['chunk_index']}")


def print_prompt(system: str, user: str) -> None:
    """Show exactly what the LLM received: instructions (system) + context and question (user)."""
    print(f"\n----- SYSTEM -----\n{system}\n\n----- USER -----\n{user}")


def main() -> None:
    # ---- 1. Define the commands and flags -------------------------------------------------------
    p = argparse.ArgumentParser(prog="rag")
    p.add_argument("--config", type=Path, default=Path("config.toml"), help="settings file (default: config.toml)")
    sub = p.add_subparsers(dest="cmd", required=True)  # exactly one of: ingest, ask

    ing = sub.add_parser("ingest", help="load, chunk, embed and store documents")
    ing.add_argument("path", type=Path, nargs="?", default=Path("data"), help="file or folder (default: data)")

    ask = sub.add_parser("ask", help="answer a question from the stored documents")
    ask.add_argument("question")
    ask.add_argument("--provider", help="override llm.provider from config for this run")
    ask.add_argument("--show-prompt", action="store_true", help="print the exact prompt sent to the LLM")
    ask.add_argument("--retrieval-only", action="store_true", help="skip the LLM, just show retrieved chunks")

    args = p.parse_args()

    # ---- 2. Load settings (config.toml + .env) --------------------------------------------------
    cfg = load_config(args.config)
    step(f"loaded config from {args.config} {args.cmd}")

    # ---- 3a. ingest: documents -> chunks -> vectors in Chroma -----------------------------------
    if args.cmd == "ingest":
        step(f"ingesting {args.path} (strategy={cfg.ingest.strategy}, chunk_tokens={cfg.ingest.chunk_tokens})")
        stats = ingest(args.path, cfg.ingest)
        step("done. Stats below: 'new' = chunks added, 'unchanged' = already stored, 'stale_removed' = old chunks deleted")
        for k, v in stats.items():
            print(f"  {k:14} {v}")
        return

    # ---- 3b. ask: question -> relevant chunks -> LLM answer -------------------------------------
    if args.provider:
        cfg.llm.provider = args.provider  # CLI flag wins over config.toml, for this run only

    step(f"question: {args.question!r}")
    step(f"searching collection '{cfg.ingest.collection}' (top_k={cfg.retrieval.top_k}, min_score={cfg.retrieval.min_score})")

    # Retrieval-only mode: stop before the LLM. Good for judging search quality in isolation.
    if args.retrieval_only:
        hits = retrieve(args.question, cfg)
        step(f"{len(hits)} chunk(s) passed the min_score filter (no LLM called)")
        for i, h in enumerate(hits, 1):
            print(f"  [{i}] score={h['score']:.2f} {h['metadata']['source']}#{h['metadata']['chunk_index']}")
            print(f"      {h['text'][:100]!r}")
        if args.show_prompt:
            print_prompt(*build_prompt(args.question, hits, cfg.llm.system_prompt))
        return

    step(f"asking LLM provider '{cfg.llm.provider}' (answer streams below)\n")
    try:
        # on_token prints each piece of the answer the moment the model produces it
        result = answer(args.question, cfg, on_token=lambda t: print(t, end="", flush=True))
    except RuntimeError as e:
        # Expected setup problems (Ollama not running, missing/bad API key) arrive as RuntimeError
        sys.exit(f"Error: {e}")

    # Nothing scored above min_score, so the LLM was never called: result.text is the fixed "I don't know".
    if not result.sources:
        step("no chunk scored above min_score, so the LLM was skipped")
        print(result.text)
        return

    step(f"\n\nanswer based on {len(result.sources)} chunk(s). Sources:")
    print_sources(result.sources)
    if args.show_prompt:
        print_prompt(result.system, result.user)


if __name__ == "__main__":
    main()
