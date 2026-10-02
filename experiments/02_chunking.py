from pathlib import Path

import tiktoken

from rag.chunking import fixed_chunks, recursive_chunks
from rag.loaders import load_dir

enc = tiktoken.get_encoding("cl100k_base")
CHUNK_TOKENS = 200


def show(name: str, chunks: list[str]) -> None:
    sizes = [len(enc.encode(c)) for c in chunks]
    print(f"\n{'=' * 70}\n{name}: {len(chunks)} chunks, tokens per chunk = {sizes}\n{'=' * 70}")
    for i, c in enumerate(chunks):
        print(f"\n--- chunk {i} ({sizes[i]} tokens) ---")
        print(f"START: {c[:80]!r}")
        print(f"END:   {c[-80:]!r}")


doc = load_dir(Path("data"))[0]
print(f"Document: {doc.metadata['source']} ({len(enc.encode(doc.text))} tokens)")

show("FIXED (200 tokens, 40 overlap)", fixed_chunks(doc.text, CHUNK_TOKENS, overlap=40))
show("RECURSIVE (max 200 tokens)", recursive_chunks(doc.text, CHUNK_TOKENS))

print("\nLook at the END lines: fixed chunks cut mid-word/sentence; recursive ones end at line/paragraph breaks.")
