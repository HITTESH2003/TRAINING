"""Recursive chunking: the purely mechanical strategy. Given a token size,
that's what gets chunked -- no understanding of meaning (that's semantic.py)
and no understanding of document structure (that's hierarchical.py). It's
still smarter than a blind character window: it tries to split on paragraph
breaks first, and if a piece is still too big, recurses into it with a finer
separator (line break, then sentence, then word) -- the same idea behind
LangChain's RecursiveCharacterTextSplitter.

But it operates on raw markdown *text*, not Module 1's layout data, so it
has no idea a `<table>` block needs to stay intact -- it will split a long
table exactly like it splits a long paragraph, because to this splitter
they're both just "a big string." That gap is deliberate: this is the
"just give me chunks of size N" baseline every RAG tutorial starts with,
and the other two strategies exist specifically to do better than it in two
different directions.

Sizing is measured in real tokens (via the same tokenizer as every other
module), not an approximated character budget -- every candidate piece is
actually tokenized and counted before a split decision is made. That's more
tokenizer calls than a char-based approximation would need (this is the
honest cost of exactness: most production recursive splitters, including
LangChain's default, approximate with characters specifically to avoid it),
but it means the reported max_tokens is a real guarantee here, not a guess
that happens to hold on any particular document.
"""

from __future__ import annotations

from . import tokenizer_util
from .config import DEFAULT_MAX_TOKENS

_SEPARATORS = ["\n\n", "\n", ". ", " "]


def _hard_cut_by_tokens(text: str, max_tokens: int) -> list[str]:
    """Last resort when no separator breaks text small enough: slice at real
    token-id boundaries and decode back, rather than guessing a character
    offset that might land mid-token."""
    tokenizer = tokenizer_util.get_tokenizer()
    ids = tokenizer(text, add_special_tokens=False)["input_ids"]
    return [tokenizer.decode(ids[i : i + max_tokens]) for i in range(0, len(ids), max_tokens)]


def _split_recursive(text: str, max_tokens: int, separators: list[str]) -> list[str]:
    if tokenizer_util.count_tokens(text) <= max_tokens:
        return [text] if text.strip() else []

    if not separators:
        return _hard_cut_by_tokens(text, max_tokens)

    sep, *rest = separators
    parts = [p for p in text.split(sep) if p != ""]
    if len(parts) <= 1:
        return _split_recursive(text, max_tokens, rest)

    pieces: list[str] = []
    buffer = ""
    for part in parts:
        candidate = f"{buffer}{sep}{part}" if buffer else part
        if tokenizer_util.count_tokens(candidate) <= max_tokens:
            buffer = candidate
        else:
            if buffer:
                pieces.append(buffer)
            if tokenizer_util.count_tokens(part) > max_tokens:
                pieces.extend(_split_recursive(part, max_tokens, rest))
                buffer = ""
            else:
                buffer = part
    if buffer:
        pieces.append(buffer)
    return pieces


def chunk_recursive(raw_text: str, doc_name: str, max_tokens: int = DEFAULT_MAX_TOKENS) -> list[dict]:
    pieces = _split_recursive(raw_text.strip(), max_tokens, _SEPARATORS)

    chunks = []
    for index, piece in enumerate(pieces):
        has_open = "<table" in piece
        has_close = "</table>" in piece
        chunks.append(
            {
                "chunk_id": f"{doc_name}__recursive__{index:04d}",
                "strategy": "recursive",
                "text": piece,
                "token_count": tokenizer_util.count_tokens(piece),
                "section_path": None,
                "pages": None,
                "block_types": None,
                "notes": ["table_split"] if has_open != has_close else [],
            }
        )
    return chunks
