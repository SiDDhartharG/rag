from rag.store import get_collection, search


def retrieve(
    query: str,
    k: int = 3,
    min_score: float = 0.0,
    where: dict | None = None,
    collection: str = "docs",
) -> list[dict]:
    """Top-k chunks for the query, dropping any scoring below `min_score`."""
    hits = search(get_collection(collection), query, k=k, where=where)
    return [h for h in hits if h["score"] >= min_score]
