"""Usage:
  uv run python -m rag.cli ingest [path]
  uv run python -m rag.cli ask "question" [--provider claude|ollama|echo] [--show-prompt] [--retrieval-only]
"""

import argparse
import sys
from pathlib import Path

from rag.config import load_config
from rag.generation import answer, build_prompt, retrieve
from rag.pipeline import ingest


def main() -> None:
    p = argparse.ArgumentParser(prog="rag")
    p.add_argument("--config", type=Path, default=Path("config.toml"))
    sub = p.add_subparsers(dest="cmd", required=True)

    ing = sub.add_parser("ingest")
    ing.add_argument("path", type=Path, nargs="?", default=Path("data"))

    ask = sub.add_parser("ask")
    ask.add_argument("question")
    ask.add_argument("--provider", help="override llm.provider from config")
    ask.add_argument("--show-prompt", action="store_true")
    ask.add_argument("--retrieval-only", action="store_true", help="skip the LLM, just show retrieved chunks")

    args = p.parse_args()
    cfg = load_config(args.config)

    if args.cmd == "ingest":
        for k, v in ingest(args.path, cfg.ingest).items():
            print(f"{k:14} {v}")
        return

    if args.provider:
        cfg.llm.provider = args.provider

    if args.retrieval_only:
        hits = retrieve(args.question, cfg)
        for i, h in enumerate(hits, 1):
            print(f"[{i}] score={h['score']:.2f} {h['metadata']['source']}#{h['metadata']['chunk_index']}")
            print(f"    {h['text'][:100]!r}")
        if args.show_prompt:
            system, user = build_prompt(args.question, hits, cfg.llm.system_prompt)
            print(f"\n----- SYSTEM -----\n{system}\n\n----- USER -----\n{user}")
        return

    try:
        result = answer(args.question, cfg, on_token=lambda t: print(t, end="", flush=True))
    except RuntimeError as e:
        sys.exit(f"Error: {e}")
    if not result.sources:
        print(result.text)
    print("\n\nSources:")
    for i, h in enumerate(result.sources, 1):
        print(f"  [{i}] score={h['score']:.2f} {h['metadata']['source']}#{h['metadata']['chunk_index']}")
    if args.show_prompt and result.sources:
        print(f"\n----- SYSTEM -----\n{result.system}\n\n----- USER -----\n{result.user}")


if __name__ == "__main__":
    main()
