from pathlib import Path

import numpy as np

from rag.chunking import (
    fixed_chunks,
    recursive_chunks,
    semantic_chunks,
    sentence_chunks,
    structure_chunks,
)
from rag.embeddings import embed
from rag.loaders import load_dir

# ---------------------------------------------------------------------------
# Part A: what is an embedding? Look at one, then compare meanings by hand.
# ---------------------------------------------------------------------------
print("=" * 70 + "\nPART A: embeddings and cosine similarity\n" + "=" * 70)

vec = embed(["I love cooking pasta"])[0]
print(f"One sentence -> vector of shape {vec.shape}")
print(f"First 8 numbers: {np.round(vec[:8], 3)}")
print(f"Length (norm): {np.linalg.norm(vec):.3f}  (1.0 => dot product == cosine similarity)")

sentences = [
    "I love cooking pasta",
    "Making spaghetti is my favourite hobby",  # same meaning, different words
    "The stock market fell sharply today",  # unrelated
    "pasta",  # keyword overlap, much shorter
    "I do not love cooking pasta",  # opposite meaning, same words
]
vecs = embed(sentences)
print("\nSimilarity of each sentence to: 'I love cooking pasta'")
for s, v in zip(sentences[1:], vecs[1:]):
    print(f"  {float(vecs[0] @ v):.2f}  {s!r}")
print("Note: the negated sentence still scores high. Embeddings capture topic more than logic.")

# ---------------------------------------------------------------------------
# Part B: does the chunking strategy change what retrieval finds?
# ---------------------------------------------------------------------------
print("\n" + "=" * 70 + "\nPART B: same questions, different chunking strategies\n" + "=" * 70)

doc = load_dir(Path("data"))[0]
CHUNK_TOKENS = 200
strategies = {
    "FIXED": fixed_chunks(doc.text, CHUNK_TOKENS, overlap=40),
    "RECURSIVE": recursive_chunks(doc.text, CHUNK_TOKENS),
    "SENTENCE": sentence_chunks(doc.text, CHUNK_TOKENS),
    "STRUCTURE": structure_chunks(doc.text, CHUNK_TOKENS),
    "SEMANTIC": semantic_chunks(doc.text, CHUNK_TOKENS)[0],
}
questions = [
    "What programming languages and tools does he know?",
    "Where did he study?",
    "What did he build at BrowserStack?",
]

chunk_vecs = {name: embed(chunks) for name, chunks in strategies.items()}

for q in questions:
    print(f"\nQUESTION: {q}")
    qv = embed([q])[0]
    for name, chunks in strategies.items():
        scores = chunk_vecs[name] @ qv  # one dot product per chunk
        best = int(np.argmax(scores))
        preview = chunks[best][:70].replace("\n", " ")
        print(f"  {name:10} best score={scores[best]:.2f}  chunk {best:>2}: {preview!r}")
