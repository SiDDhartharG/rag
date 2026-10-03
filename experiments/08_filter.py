"""Metadata filtering: the `where` clause restricts WHICH chunks are searched; similarity then
ranks only the survivors. Uses a throwaway in-memory collection with a few toy chunks."""

import chromadb

from rag.embeddings import embed
from rag.store import search

col = chromadb.EphemeralClient().get_or_create_collection(
    "filter_demo", configuration={"hnsw": {"space": "cosine"}}
)

# (text, metadata) -- the metadata is NOT part of the embedded text
rows = [
    ("Refunds are issued within 14 days of purchase.", {"doc": "policy", "year": 2023, "team": "support"}),
    ("Refunds are issued within 30 days of purchase.", {"doc": "policy", "year": 2025, "team": "support"}),
    ("Employees get 20 days of paid leave per year.", {"doc": "handbook", "year": 2025, "team": "hr"}),
    ("The refund API endpoint is POST /v1/refunds.", {"doc": "api", "year": 2025, "team": "eng"}),
]
col.add(
    ids=[str(i) for i in range(len(rows))],
    embeddings=embed([t for t, _ in rows]).tolist(),
    documents=[t for t, _ in rows],
    metadatas=[m for _, m in rows],
)

q = "How long do refunds take?"


def run(label: str, where: dict | None) -> None:
    print(f"\n{label}   where={where}")
    for h in search(col, q, k=4, where=where):
        print(f"  {h['score']:.2f}  {h['metadata']}  {h['text']!r}")


print(f"QUESTION: {q}")
run("1. No filter (ranks all 4 chunks)", None)
run("2. Only year 2025 (drops the outdated 14-day policy)", {"year": 2025})
run("3. Only doc=policy AND year>=2024", {"$and": [{"doc": "policy"}, {"year": {"$gte": 2024}}]})
run("4. Only team in [hr, eng]", {"team": {"$in": ["hr", "eng"]}})
run("5. Filter matches nothing", {"doc": "nonexistent"})

print("\nNote: filtering is exact matching on metadata, not meaning. 'year': 2025 either matches or not.")
