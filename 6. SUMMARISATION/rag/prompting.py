"""Builds the actual RAG prompt: retrieved chunks, source-attributed and
numbered, followed by the question and an explicit instruction to answer
only from the given context. This is deliberately visible and inspectable
-- the Streamlit app shows this exact text, not a black-box summary of it.
"""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a document assistant. Answer the user's question using ONLY the "
    "numbered source excerpts provided below. If the excerpts don't contain "
    "enough information to answer, say so explicitly rather than guessing. "
    "Cite sources by their [N] number when you use them."
)


def build_context_block(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        location = chunk["doc_name"]
        if chunk.get("section_path"):
            location += f" > {chunk['section_path']}"
        parts.append(f"[{i}] (source: {location})\n{chunk['chunk_text']}")
    return "\n\n".join(parts)


def build_messages(question: str, chunks: list[dict]) -> list[dict]:
    context_block = build_context_block(chunks)
    user_content = f"Source excerpts:\n\n{context_block}\n\nQuestion: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
