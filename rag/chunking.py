import re

import numpy as np
import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def fixed_chunks(text: str, chunk_tokens: int = 200, overlap: int = 40) -> list[str]:
    """Slide a window of `chunk_tokens` tokens, stepping by chunk_tokens - overlap."""
    ids = _enc.encode(text)
    step = chunk_tokens - overlap
    chunks = []
    for start in range(0, len(ids), step):
        # Decode via bytes: a token cut can land inside a multi-byte character (e.g. Hindi);
        # dropping the partial edge bytes is safe because the overlap holds the whole character.
        raw = _enc.decode_bytes(ids[start : start + chunk_tokens])
        chunks.append(raw.decode("utf-8", errors="ignore"))
        if start + chunk_tokens >= len(ids):  # window reached the end; the next would be pure overlap
            break
    return chunks


def _count(text: str) -> int:
    return len(_enc.encode(text))


def recursive_chunks(
    text: str,
    chunk_tokens: int = 200,
    separators: tuple[str, ...] = ("\n\n", "\n", ". ", " "),
) -> list[str]:
    """Split on the biggest separator first; only go finer for pieces that are still too big,
    then merge small neighbours back together up to chunk_tokens."""
    if _count(text) <= chunk_tokens or not separators:
        return [text.strip()] if text.strip() else []

    sep, finer = separators[0], separators[1:]
    pieces: list[str] = []
    for part in text.split(sep):
        pieces.extend(recursive_chunks(part, chunk_tokens, finer))

    chunks: list[str] = []
    current = ""
    for piece in pieces:
        candidate = f"{current}{sep}{piece}" if current else piece
        if current and _count(candidate) > chunk_tokens:
            chunks.append(current)
            current = piece
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def split_sentences(text: str) -> list[str]:
    """Split on sentence punctuation or line breaks; glue lone bullet marks to the next line."""
    text = re.sub(r"[•\-\*]\s*\n", "• ", text)
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def _pack(units: list[str], chunk_tokens: int, joiner: str) -> list[str]:
    """Greedily pack whole units into chunks up to chunk_tokens (an oversized unit stays alone)."""
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}{joiner}{unit}" if current else unit
        if current and _count(candidate) > chunk_tokens:
            chunks.append(current)
            current = unit
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def sentence_chunks(text: str, chunk_tokens: int = 200) -> list[str]:
    """Never cuts inside a sentence: pack whole sentences until the token budget is full."""
    return _pack(split_sentences(text), chunk_tokens, " ")


_HEADING = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Z &/]{2,})$")


def structure_chunks(text: str, chunk_tokens: int = 200) -> list[str]:
    """Split at headings (markdown '#' lines or ALL-CAPS lines like 'EDUCATION'). Sections that
    are still too big are sub-split, and the heading is repeated on every piece for context."""
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in text.splitlines():
        if _HEADING.match(line.strip()):
            sections.append((line.strip(), []))
        else:
            sections[-1][1].append(line)

    chunks: list[str] = []
    for heading, lines in sections:
        body = "\n".join(lines).strip()
        if not body:
            continue
        budget = chunk_tokens - _count(heading)
        for piece in recursive_chunks(body, budget):
            chunks.append(f"{heading}\n{piece}" if heading else piece)
    return chunks


def semantic_chunks(
    text: str, chunk_tokens: int = 200, percentile: float = 25.0
) -> tuple[list[str], list[float]]:
    """Embed each sentence, then start a new chunk wherever similarity to the previous sentence
    falls in the lowest `percentile` % (a topic shift). Also splits when a chunk hits the cap.
    Returns (chunks, similarities) so the experiment can show where and why it split."""
    from rag.embeddings import embed

    sentences = split_sentences(text)
    vecs = embed(sentences)
    sims = [float(vecs[i] @ vecs[i + 1]) for i in range(len(sentences) - 1)]
    cutoff = float(np.percentile(sims, percentile))

    chunks: list[str] = []
    current = [sentences[0]]
    for sent, sim in zip(sentences[1:], sims):
        too_big = _count(" ".join(current + [sent])) > chunk_tokens
        if sim < cutoff or too_big:
            chunks.append(" ".join(current))
            current = [sent]
        else:
            current.append(sent)
    chunks.append(" ".join(current))
    return chunks, sims
