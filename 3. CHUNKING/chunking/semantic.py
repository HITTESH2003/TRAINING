"""Semantic chunking: group consecutive blocks by how similar their meaning
is, not by document structure or a blind size window.

This is the third distinct technique alongside recursive.py and
hierarchical.py, and it's worth being precise about what makes it different
from both:

  - recursive.py doesn't look at meaning at all -- it just respects text
    boundaries (paragraphs/sentences) inside a token budget.
  - hierarchical.py uses the document's declared structure (headings) to
    decide what belongs together, then sizes within that.
  - semantic.py ignores headings entirely and decides purely from content:
    embed each block, compare it to the block before it (cosine similarity
    of L2-normalized vectors, i.e. a dot product), and start a new chunk
    wherever that similarity drops below a threshold -- a topic shift,
    detected from the text itself, not from a `##` a layout model happened
    to draw a box around.

Tables and figures still stay atomic (never split, never merged across
their boundary into a similarity comparison) -- that discipline doesn't
change just because the boundary-finding technique did. Each chunk records
the similarity score that ended it (`boundary_similarity`), so a "why did
it split here" question has a real number to point at instead of a guess.

The 0.5 default threshold is not a universal constant -- it's a starting
point for Qwen3-Embedding-0.6B's similarity distribution on prose-heavy
documents. Tune it per document type; too high and everything becomes its
own chunk, too low and unrelated paragraphs get glued together.
"""

from __future__ import annotations

from . import embedding_util, tokenizer_util
from .blocks import Block
from .config import DEFAULT_MAX_TOKENS, DEFAULT_SIMILARITY_THRESHOLD


def _low_confidence_note(blocks: list[Block]) -> list[str]:
    if any(b.extra.get("low_confidence") for b in blocks):
        return ["contains_low_confidence_region"]
    return []


def _make_chunk(doc_name: str, index: int, buffer_blocks: list[Block], boundary_similarity: float | None, notes: list[str]) -> dict:
    text = "\n".join(b.text for b in buffer_blocks)
    pages = sorted({b.page for b in buffer_blocks if b.page is not None})
    types = [b.type for b in buffer_blocks]
    return {
        "chunk_id": f"{doc_name}__semantic__{index:04d}",
        "strategy": "semantic",
        "text": text,
        "token_count": tokenizer_util.count_tokens(text),
        "section_path": None,  # semantic chunking deliberately doesn't use heading structure
        "pages": pages,
        "block_types": types,
        "boundary_similarity": boundary_similarity,
        "notes": notes + _low_confidence_note(buffer_blocks),
    }


def chunk_semantic(
    blocks: list[Block],
    doc_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[dict]:
    chunks: list[dict] = []
    index = 0
    buffer_blocks: list[Block] = []
    buffer_tokens = 0
    prev_embedding = None

    def flush(boundary_similarity: float | None, notes: list[str] | None = None) -> None:
        nonlocal buffer_blocks, buffer_tokens, index
        if not buffer_blocks:
            return
        chunks.append(_make_chunk(doc_name, index, buffer_blocks, boundary_similarity, list(notes or [])))
        index += 1
        buffer_blocks = []
        buffer_tokens = 0

    for block in blocks:
        if block.type in ("table", "figure"):
            # Atomic: always its own chunk, never compared into the similarity
            # chain -- a table doesn't have a "topic" to be similar or
            # dissimilar to the surrounding prose.
            flush(None)
            chunks.append(_make_chunk(doc_name, index, [block], None, ["atomic_block"]))
            index += 1
            prev_embedding = None  # don't compare the next paragraph's topic across a table
            continue

        embedding = embedding_util.embed_text(block.text)
        block_tokens = tokenizer_util.count_tokens(block.text)

        if not buffer_blocks and block_tokens > max_tokens:
            # A single block already over budget: give it its own chunk rather
            # than silently starting an oversized one -- flagged the same way
            # hierarchical.py flags an oversized atomic block, for consistency.
            chunks.append(_make_chunk(doc_name, index, [block], None, ["oversized_block"]))
            index += 1
            prev_embedding = embedding
            continue

        if buffer_blocks:
            similarity = embedding_util.cosine_similarity(prev_embedding, embedding)
            over_budget = buffer_tokens + block_tokens > max_tokens
            topic_shift = similarity < similarity_threshold
            if topic_shift or over_budget:
                flush(similarity, ["over_budget"] if over_budget and not topic_shift else [])

        buffer_blocks.append(block)
        buffer_tokens += block_tokens
        prev_embedding = embedding

    flush(None)
    return chunks
