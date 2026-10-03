import hashlib
from pathlib import Path

import chromadb

from rag.embeddings import embed

CHROMA_PATH = Path("data/chroma")


def get_collection(name: str = "docs", path: Path = CHROMA_PATH):
    client = chromadb.PersistentClient(path=str(path))
    # cosine space => distance = 1 - cosine similarity (Chroma's default is L2)
    return client.get_or_create_collection(name, configuration={"hnsw": {"space": "cosine"}})


def chunk_id(source: str, text: str) -> str:
    """Stable ID from content: the same chunk always gets the same ID, so re-ingesting overwrites
    instead of duplicating."""
    return hashlib.sha1(f"{source}\n{text}".encode()).hexdigest()[:16]


def add_chunks(collection, chunks: list[str], source: str) -> None:
    collection.upsert(
        ids=[chunk_id(source, c) for c in chunks],
        embeddings=embed(chunks).tolist(),
        documents=chunks,
        metadatas=[{"source": source, "chunk_index": i} for i in range(len(chunks))],
    )


def search(collection, query: str, k: int = 3) -> list[dict]:
    res = collection.query(query_embeddings=embed([query]).tolist(), n_results=k)
    return [
        {"score": 1 - dist, "text": doc, "metadata": meta}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
