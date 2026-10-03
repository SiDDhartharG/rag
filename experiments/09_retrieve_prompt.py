from pathlib import Path

from rag.generation import build_prompt
from rag.pipeline import IngestConfig, ingest
from rag.retrieval import retrieve
from rag.store import get_collection

if get_collection("docs").count() == 0:
    ingest(Path("data"), IngestConfig(strategy="structure"))

# 1. Scores for answerable vs unanswerable questions: where should a cutoff go?
print("=" * 70 + "\n1. Best score per question (to choose a threshold)\n" + "=" * 70)
questions = [
    "What programming languages and tools does he know?",
    "Where did he study?",
    "What did he build at BrowserStack?",
    "What is the capital of France?",
    "How do I bake sourdough bread?",
    "What is the weather today?",
]
for q in questions:
    hits = retrieve(q, k=3)
    print(f"  top={hits[0]['score']:.2f}  2nd={hits[1]['score']:.2f}  3rd={hits[2]['score']:.2f}  {q!r}")

# 2. Metadata filter
print("\n" + "=" * 70 + "\n2. Metadata filter\n" + "=" * 70)
print("  filter source='nope.pdf' ->", retrieve("Where did he study?", where={"source": "nope.pdf"}))

# 3. The exact prompt the LLM will receive
print("\n" + "=" * 70 + "\n3. The prompt sent to the LLM\n" + "=" * 70)
q = "What programming languages and tools does he know?"
system, user = build_prompt(q, retrieve(q, k=3))
print("--- SYSTEM ---\n" + system)
print("\n--- USER ---\n" + user)
