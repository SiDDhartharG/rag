from collections.abc import Callable
from dataclasses import dataclass

from rag.config import RagConfig
from rag.llm import LLMClient, get_llm
from rag.retrieval import retrieve as _retrieve

NO_ANSWER = "I don't know: nothing in the indexed documents is relevant enough to this question."

DEFAULT_SYSTEM_PROMPT = (
    "You answer questions using ONLY the numbered context passages provided. "
    "Cite the passages you used like [1] or [2][3]. "
    "If the context does not contain the answer, say you don't know."
)


@dataclass
class Answer:
    text: str
    sources: list[dict]
    system: str  # what the LLM was told
    user: str  # the context + question it saw (great for debugging)


def retrieve(question: str, cfg: RagConfig) -> list[dict]:
    """Config-driven wrapper around rag.retrieval.retrieve."""
    return _retrieve(
        question,
        k=cfg.retrieval.top_k,
        min_score=cfg.retrieval.min_score,
        collection=cfg.ingest.collection,
    )


def build_prompt(question: str, hits: list[dict], system_prompt: str | None = None) -> tuple[str, str]:
    """Return (system, user). Chunks are numbered so the model can cite [1], [2]."""
    context = "\n\n".join(f"[{i}] (source: {h['metadata']['source']})\n{h['text']}" for i, h in enumerate(hits, 1))
    return system_prompt or DEFAULT_SYSTEM_PROMPT, f"Context:\n{context}\n\nQuestion: {question}"


def answer(
    question: str,
    cfg: RagConfig,
    llm: LLMClient | None = None,
    on_token: Callable[[str], None] | None = None,
) -> Answer:
    hits = retrieve(question, cfg)
    if not hits:
        return Answer(NO_ANSWER, [], "", "")  # skip the LLM entirely: nothing to ground an answer on

    system, user = build_prompt(question, hits, cfg.llm.system_prompt)
    llm = llm or get_llm(cfg.llm)
    pieces = []
    for piece in llm.stream(system, user):
        pieces.append(piece)
        if on_token:
            on_token(piece)
    return Answer("".join(pieces), hits, system, user)
