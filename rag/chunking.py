import tiktoken

_enc = tiktoken.get_encoding("cl100k_base")


def fixed_chunks(text: str, chunk_tokens: int = 200, overlap: int = 40) -> list[str]:
    """Slide a window of `chunk_tokens` tokens, stepping by chunk_tokens - overlap."""
    ids = _enc.encode(text)
    step = chunk_tokens - overlap
    return [_enc.decode(ids[i : i + chunk_tokens]) for i in range(0, len(ids), step)]


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
