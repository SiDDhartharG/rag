from pathlib import Path

from rag.pipeline import IngestConfig, ingest
from rag.store import get_collection


def show(title: str, stats: dict) -> None:
    print(f"\n--- {title} ---")
    for k, v in stats.items():
        print(f"  {k:14} {v}")


# Start clean so the demo is predictable
col = get_collection("demo")
if col.count():
    col.delete(ids=col.get()["ids"])

data = Path("data")

show("1. First ingest (structure)", ingest(data, IngestConfig(strategy="structure", collection="demo")))
show("2. Same again: everything should be 'unchanged'", ingest(data, IngestConfig(strategy="structure", collection="demo")))
show("3. Switch strategy to recursive: old chunks become stale and are removed",
     ingest(data, IngestConfig(strategy="recursive", collection="demo")))
show("4. Smaller chunks (100 tokens): more chunks",
     ingest(data, IngestConfig(strategy="recursive", chunk_tokens=100, collection="demo")))

try:
    ingest(data, IngestConfig(strategy="bogus", collection="demo"))
except ValueError as e:
    print(f"\n5. Bad strategy is rejected: {e}")
