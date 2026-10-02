from pathlib import Path

import numpy as np
import tiktoken

from rag.chunking import (
    fixed_chunks,
    recursive_chunks,
    semantic_chunks,
    sentence_chunks,
    split_sentences,
    structure_chunks,
)
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
print(123,doc)
print(f"Document: {doc.metadata['source']} ({len(enc.encode(doc.text))} tokens)")

sentences = split_sentences(doc.text)
print(f"\nSplit into {len(sentences)} sentence-units. First 5: ")
for s in sentences[:5]:
    print("  ", repr(s[:90]))

results = {
    "FIXED (200 tok, 40 overlap)": fixed_chunks(doc.text, CHUNK_TOKENS, overlap=100),
    "RECURSIVE (max 200)": recursive_chunks(doc.text, CHUNK_TOKENS),
    "SENTENCE (pack whole sentences, max 200)": sentence_chunks(doc.text, CHUNK_TOKENS),
    "STRUCTURE (split at headings, max 200)": structure_chunks(doc.text, CHUNK_TOKENS),
}
sem_chunks, sims = semantic_chunks(doc.text, CHUNK_TOKENS)
results["SEMANTIC (split at topic shifts, max 200)"] = sem_chunks

for name, chunks in results.items():
    show(name, chunks)

print(f"\n{'=' * 70}\nSEMANTIC detail: similarity between consecutive sentences\n{'=' * 70}")
print(f"mean={np.mean(sims):.2f}  min={min(sims):.2f}  25th percentile cutoff={np.percentile(sims, 25):.2f}")
print("Lowest-similarity boundaries (where it prefers to split):")
for i in np.argsort(sims)[:5]:
    print(f"  sim={sims[i]:.2f}  {sentences[i][:45]!r}  ||  {sentences[i + 1][:45]!r}")

print(f"\n{'=' * 70}\nSUMMARY\n{'=' * 70}")
print(f"{'strategy':45} {'chunks':>6} {'min':>5} {'max':>5}")
for name, chunks in results.items():
    sizes = [len(enc.encode(c)) for c in chunks]
    print(f"{name:45} {len(chunks):>6} {min(sizes):>5} {max(sizes):>5}")
