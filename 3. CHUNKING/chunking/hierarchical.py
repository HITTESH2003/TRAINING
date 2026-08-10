"""Content-aware hierarchical chunking -- the main point of this module.

'Hierarchical' here does NOT mean "one chunk per header." A pure
header-split chunker would respect document structure but not care at all
how much content is in each section, producing near-empty chunks next to
oversized ones on the exact same document. Hierarchical chunking means two
things happening together:

  1. STRUCTURE gives you the hierarchy: headings define a breadcrumb path
     (section_path) that every chunk under them carries as metadata, and
     tables/figures are treated as atomic blocks that are never split
     mid-content, because chopping a `<table>` in half doesn't produce two
     meaningful halves -- it produces two broken fragments.

  2. CONTENT decides the actual chunk boundaries within that structure: blocks
     are packed together up to a token budget, a paragraph too large for the
     budget on its own gets recursively split (falling back to recursive.py's
     splitter, at sentence granularity, not mid-header), and small trailing
     fragments get merged into their neighbor instead of standing alone.

So a heading with no content under it produces no chunk at all (nothing to
read the content of), a heading with nine long paragraphs under it produces
several appropriately-sized chunks instead of one oversized one, and a table
stays exactly as intact as it was when Module 1 extracted it -- whether the
chunk it lands in is otherwise big or small.

Blocks built from Module 1's regions.json (see layout_blocks.py) also carry
each source region's OCR confidence. Any chunk assembled even partly from a
low-confidence region is flagged `contains_low_confidence_region` -- a
concrete reason to prefer real layout data over re-parsing markdown text,
which has no way to know a region's confidence at all.
"""

from __future__ import annotations

from . import tokenizer_util
from .blocks import Block
from .config import DEFAULT_MAX_TOKENS, DEFAULT_MIN_TOKENS
from .recursive import _SEPARATORS, _split_recursive


def _build_sections(blocks: list[Block]) -> list[dict]:
    """Groups content blocks under the heading path active when they appeared.
    A heading with nothing under it before the next heading produces no
    section at all -- there's no content to chunk."""
    sections: list[dict] = []
    stack: list[tuple[int, str]] = []
    current: list[Block] = []

    def path() -> list[str]:
        return [text for level, text in stack if level >= 2]

    def flush() -> None:
        if current:
            sections.append({"path": path(), "blocks": list(current)})
            current.clear()

    for block in blocks:
        if block.type == "heading":
            flush()
            while stack and stack[-1][0] >= block.level:
                stack.pop()
            stack.append((block.level, block.text))
            continue
        current.append(block)

    flush()
    return sections


def _make_chunk(doc_name: str, index: int, text: str, section_path: list[str], pages: list[int], block_types: list[str], notes: list[str]) -> dict:
    context = " > ".join(section_path) if section_path else doc_name
    return {
        "chunk_id": f"{doc_name}__hierarchical__{index:04d}",
        "strategy": "hierarchical",
        "text": text,
        "contextualized_text": f"[{context}]\n{text}",
        "token_count": tokenizer_util.count_tokens(text),
        "section_path": section_path,
        "pages": pages,
        "block_types": block_types,
        "notes": notes,
    }


def _low_confidence_note(blocks: list[Block]) -> list[str]:
    if any(b.extra.get("low_confidence") for b in blocks):
        return ["contains_low_confidence_region"]
    return []


def _pack_section(section_blocks: list[Block], section_path: list[str], doc_name: str, max_tokens: int, start_index: int) -> tuple[list[dict], int]:
    chunks: list[dict] = []
    buffer_blocks: list[Block] = []
    buffer_tokens = 0
    index = start_index

    def flush_buffer() -> None:
        nonlocal buffer_blocks, buffer_tokens, index
        if not buffer_blocks:
            return
        text = "\n".join(b.text for b in buffer_blocks)
        pages = sorted({b.page for b in buffer_blocks if b.page is not None})
        types = [b.type for b in buffer_blocks]
        chunks.append(_make_chunk(doc_name, index, text, section_path, pages, types, _low_confidence_note(buffer_blocks)))
        index += 1
        buffer_blocks = []
        buffer_tokens = 0

    for block in section_blocks:
        block_tokens = tokenizer_util.count_tokens(block.text)

        if block.type in ("table", "figure"):
            # Atomic: never split. If it doesn't fit alongside what's buffered,
            # the buffer closes out first and the atomic block starts fresh --
            # possibly alone, possibly even over budget, but always intact.
            if buffer_blocks and buffer_tokens + block_tokens > max_tokens:
                flush_buffer()
            if block_tokens > max_tokens:
                flush_buffer()
                pages = [block.page] if block.page is not None else []
                notes = ["oversized_atomic"] + _low_confidence_note([block])
                chunks.append(_make_chunk(doc_name, index, block.text, section_path, pages, [block.type], notes))
                index += 1
            else:
                buffer_blocks.append(block)
                buffer_tokens += block_tokens
            continue

        # Paragraph too large to ever fit a chunk on its own: fall back to
        # sentence-level recursive splitting, same technique recursive.py
        # uses -- but only ever applied *within* one paragraph, never across
        # a heading or into a table.
        if block_tokens > max_tokens:
            flush_buffer()
            pieces = _split_recursive(block.text, max_tokens, _SEPARATORS)
            pages = [block.page] if block.page is not None else []
            notes = ["paragraph_split_for_size"] + _low_confidence_note([block])
            for piece in pieces:
                chunks.append(_make_chunk(doc_name, index, piece, section_path, pages, ["paragraph"], list(notes)))
                index += 1
            continue

        if buffer_blocks and buffer_tokens + block_tokens > max_tokens:
            flush_buffer()
        buffer_blocks.append(block)
        buffer_tokens += block_tokens

    flush_buffer()
    return chunks, index


def _merge_small_trailing_chunks(chunks: list[dict], min_tokens: int) -> list[dict]:
    merged: list[dict] = []
    for chunk in chunks:
        prev = merged[-1] if merged else None
        can_merge = (
            prev is not None
            and chunk["token_count"] < min_tokens
            and "oversized_atomic" not in chunk["notes"]
            and "oversized_atomic" not in prev["notes"]
            and prev["section_path"] == chunk["section_path"]
        )
        if can_merge:
            prev["text"] = prev["text"] + "\n" + chunk["text"]
            context = " > ".join(prev["section_path"]) if prev["section_path"] else ""
            prev["contextualized_text"] = f"[{context}]\n{prev['text']}" if context else prev["text"]
            prev["token_count"] = tokenizer_util.count_tokens(prev["text"])
            prev["pages"] = sorted(set(prev["pages"]) | set(chunk["pages"]))
            prev["block_types"] = prev["block_types"] + chunk["block_types"]
            prev["notes"] = sorted(set(prev["notes"]) | set(chunk["notes"]) | {"merged_small_chunk"})
        else:
            merged.append(dict(chunk))
    return merged


def chunk_hierarchical(
    blocks: list[Block],
    doc_name: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    min_tokens: int = DEFAULT_MIN_TOKENS,
) -> list[dict]:
    sections = _build_sections(blocks)

    all_chunks: list[dict] = []
    next_index = 0
    for section in sections:
        section_chunks, next_index = _pack_section(section["blocks"], section["path"], doc_name, max_tokens, next_index)
        all_chunks.extend(section_chunks)

    all_chunks = _merge_small_trailing_chunks(all_chunks, min_tokens)

    # Re-sequence ids/section-scoped index now that merging may have dropped some.
    for i, chunk in enumerate(all_chunks):
        chunk["chunk_id"] = f"{doc_name}__hierarchical__{i:04d}"

    return all_chunks
