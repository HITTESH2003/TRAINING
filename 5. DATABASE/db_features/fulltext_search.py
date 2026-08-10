"""Postgres has a real, built-in keyword search engine -- tsvector/tsquery,
with GIN indexes and ts_rank scoring -- entirely separate from pgvector.
This demo runs the SAME queries through full-text search and vector search
side by side, on the real chunks table, so the difference in what each one
is actually good at is visible rather than asserted:

  - Full-text search wins on exact, specific terms (a document ID, a
    percentage figure, a proper noun) -- it's matching words, not meaning.
  - Vector search wins on paraphrase and topic ("space station research"
    finding a chunk that never uses those exact words) -- it's matching
    meaning, not words.

Neither replaces the other. Most real systems use both (hybrid search).
"""

from __future__ import annotations

from pgvector import Vector

from . import config
from .connection import embed_query


def ensure_fulltext_index(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE chunks ADD COLUMN IF NOT EXISTS chunk_text_tsv tsvector
                GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED;
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (chunk_text_tsv);")
    conn.commit()


def fulltext_search(conn, query_text: str, top_k: int = 5) -> list[dict]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT chunk_id, doc_name,
                   ts_rank(chunk_text_tsv, websearch_to_tsquery('english', %s)) AS rank
            FROM chunks
            WHERE chunk_text_tsv @@ websearch_to_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s;
            """,
            [query_text, query_text, top_k],
        )
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def vector_search(conn, query_text: str, dim: int = config.DEFAULT_DIM, top_k: int = 5) -> list[dict]:
    query_vec = Vector(embed_query(query_text, dim))
    column = f"embedding_{dim}"
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT chunk_id, doc_name, {column} <=> %s AS distance
            FROM chunks
            ORDER BY {column} <=> %s
            LIMIT %s;
            """,
            [query_vec, query_vec, top_k],
        )
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def compare(conn, query_text: str, dim: int = config.DEFAULT_DIM, top_k: int = 3) -> dict:
    return {
        "query": query_text,
        "fulltext_results": fulltext_search(conn, query_text, top_k=top_k),
        "vector_results": vector_search(conn, query_text, dim=dim, top_k=top_k),
    }
