import time
from dataclasses import asdict, dataclass
from pathlib import Path

from rag.chunking import (
    fixed_chunks,
    recursive_chunks,
    semantic_chunks,
    sentence_chunks,
    structure_chunks,
)
from rag.loaders import load_dir, load_file
from rag.store import add_chunks, chunk_id, get_collection

STRATEGIES = {
    "fixed": lambda text, c: fixed_chunks(text, c.chunk_tokens, c.overlap),
    "recursive": lambda text, c: recursive_chunks(text, c.chunk_tokens),
    "sentence": lambda text, c: sentence_chunks(text, c.chunk_tokens),
    "structure": lambda text, c: structure_chunks(text, c.chunk_tokens),
    "semantic": lambda text, c: semantic_chunks(text, c.chunk_tokens)[0],
}


@dataclass
class IngestConfig:
    strategy: str = "structure"
    chunk_tokens: int = 200
    overlap: int = 40  # only used by "fixed"
    collection: str = "docs"


def ingest(path: Path, config: IngestConfig | None = None) -> dict:
    """Load -> chunk -> embed -> store a file or a folder. Safe to re-run: unchanged chunks are
    overwritten in place, and chunks that no longer exist in a re-ingested file are removed."""
    config = config or IngestConfig()
    if config.strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy {config.strategy!r}; choose from {list(STRATEGIES)}")

    start = time.perf_counter()
    col = get_collection(config.collection)
    docs = load_dir(path) if path.is_dir() else [load_file(path)]
    stats = {"config": asdict(config), "files": 0, "chunks": 0, "new": 0, "unchanged": 0, "stale_removed": 0}

    for doc in docs:
        source = doc.metadata["source"]
        chunks = STRATEGIES[config.strategy](doc.text, config)
        new_ids = [chunk_id(source, c) for c in chunks]

        existing = set(col.get(ids=new_ids)["ids"])
        stale = [i for i in col.get(where={"source": source})["ids"] if i not in set(new_ids)]
        if stale:
            col.delete(ids=stale)

        add_chunks(col, chunks, source)
        stats["files"] += 1
        stats["chunks"] += len(chunks)
        stats["unchanged"] += len(existing)
        stats["new"] += len(set(new_ids) - existing)
        stats["stale_removed"] += len(stale)

    stats["total_in_db"] = col.count()
    stats["seconds"] = round(time.perf_counter() - start, 2)
    return stats
