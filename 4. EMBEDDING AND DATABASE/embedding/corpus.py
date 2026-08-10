"""Loads Module 3's hierarchical chunks as the corpus to embed and store.

hierarchical specifically -- of the three chunking strategies, it's the one
with real section context (section_path) and no split tables/figures, which
makes it the most sensible corpus for a retrieval experiment. This module
doesn't re-implement chunking; it just reads what Module 3 already produced.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import config


def load_corpus(chunking_output_dir: Path = config.DEFAULT_CHUNKING_OUTPUT_DIR) -> list[dict]:
    corpus = []
    for doc_dir in sorted(chunking_output_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        chunk_path = doc_dir / "hierarchical.json"
        if not chunk_path.exists():
            continue
        chunks = json.loads(chunk_path.read_text(encoding="utf-8"))
        for chunk in chunks:
            corpus.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "doc_name": doc_dir.name,
                    "section_path": " > ".join(chunk["section_path"]) if chunk.get("section_path") else "",
                    "text": chunk["text"],
                }
            )
    return corpus
