"""Run this script TWICE. The second run proves the data persisted on disk and that
re-ingesting does not create duplicates."""

from pathlib import Path

from rag.chunking import structure_chunks
from rag.loaders import load_dir
from rag.store import CHROMA_PATH, add_chunks, chunk_id, get_collection, search

col = get_collection()
print(f"Chroma folder: {CHROMA_PATH}  | chunks already stored before this run: {col.count()}")

# --- Ingest: load -> chunk -> embed -> store ---
for doc in load_dir(Path("data")):
    source = doc.metadata["source"]
    chunks = structure_chunks(doc.text, 200)
    add_chunks(col, chunks, source)
    print(f"Ingested {source}: {len(chunks)} chunks")

print(f"Chunks stored after this run: {col.count()}  (same as before => no duplicates)")

# --- Look inside what was stored ---
print("\nStored records (first 20):")
rec = col.get(limit=20, include=["documents", "metadatas", "embeddings"])
for i in range(len(rec["ids"])):
    print(f"  id={rec['ids'][i]}  metadata={rec['metadatas'][i]}")
    print(f"     vector: {len(rec['embeddings'][i])} numbers, first 3 = {[round(float(x), 3) for x in rec['embeddings'][i][:3]]}")
    print(f"     text:   {rec['documents'][i][:60]!r}")

# --- Search: this is the same dot-product ranking as before, done by Chroma ---
for q in ["What programming languages and tools does he know?", "Where did he study?"]:
    print(f"\nQUESTION: {q}")
    for rank, hit in enumerate(search(col, q, k=3), 1):
        print(f"  #{rank} score={hit['score']:.2f} chunk_index={hit['metadata']['chunk_index']} {hit['text']}")

# --- Stable IDs: same text -> same ID, changed text -> new ID ---
print("\nStable IDs:")
print("  same text  :", chunk_id("a.pdf", "hello"), chunk_id("a.pdf", "hello"))
print("  edited text:", chunk_id("a.pdf", "hello!"))
