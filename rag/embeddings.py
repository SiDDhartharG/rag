from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_model(name: str = MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(name)


def embed(texts: list[str]) -> np.ndarray:
    """Return unit-length vectors, shape (len(texts), 384), so dot product == cosine similarity."""
    return get_model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
