"""Metadata-filtered vector search: combine a WHERE clause on ordinary
columns (doc_name, section_path) with an ORDER BY on the vector column.
This is the pattern real retrieval systems actually use -- "find content
similar to X, but only within document Y / only from section Z" -- and it's
just SQL, no special pgvector syntax needed beyond the vector column itself.
"""

from __future__ import annotations

from pgvector import Vector

from . import config
from .connection import embed_query


def search(conn, query_text: str, dim: int = config.DEFAULT_DIM, doc_name: str | None = None, top_k: int = 5) -> list[dict]:
    query_vec = Vector(embed_query(query_text, dim))
    column = f"embedding_{dim}"

    where_clause = "WHERE doc_name = %s" if doc_name else ""
    params = [query_vec]
    if doc_name:
        params.append(doc_name)
    params += [query_vec, top_k]

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT chunk_id, doc_name, section_path, {column} <=> %s AS distance
            FROM chunks
            {where_clause}
            ORDER BY {column} <=> %s
            LIMIT %s;
            """,
            params,
        )
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def compare_filtered_vs_unfiltered(conn, query_text: str, doc_name: str, dim: int = config.DEFAULT_DIM, top_k: int = 3) -> dict:
    """Runs the same query with and without a doc_name filter, so you can see
    whether restricting to one document actually changes the top result --
    not just assert that filtering "works", show whether it mattered."""
    unfiltered = search(conn, query_text, dim=dim, doc_name=None, top_k=top_k)
    filtered = search(conn, query_text, dim=dim, doc_name=doc_name, top_k=top_k)
    changed = unfiltered[0]["chunk_id"] != filtered[0]["chunk_id"]
    return {
        "query": query_text,
        "doc_name_filter": doc_name,
        "unfiltered_top1": unfiltered[0],
        "filtered_top1": filtered[0],
        "top1_changed_by_filter": changed,
        "unfiltered_results": unfiltered,
        "filtered_results": filtered,
    }
