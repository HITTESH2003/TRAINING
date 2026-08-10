"""Postgres + pgvector storage: one row per chunk, one vector column per
dimension we're testing. A single table with parallel columns (rather than
one table per dimension) keeps "same chunk, different dimension" a simple
column lookup instead of a join -- appropriate for a small teaching corpus.
"""

from __future__ import annotations

from . import config

_DIM_COLUMNS = {dim: f"embedding_{dim}" for dim in config.TEST_DIMENSIONS}


def connect():
    import psycopg
    from pgvector.psycopg import register_vector

    conn = psycopg.connect(config.pg_dsn())
    # register_vector() looks up the `vector` type in pg_type, so the
    # extension has to exist first -- safe to run every connect(), it's a
    # no-op after the first time (CREATE EXTENSION IF NOT EXISTS).
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    # Without this, psycopg has no idea how to adapt a Python list/array into
    # pgvector's `vector` input format -- it would try to send it as a
    # Postgres ARRAY literal, which is a different type and fails silently
    # wrong (or errors) against a `vector` column.
    register_vector(conn)
    return conn


def init_schema(conn) -> None:
    dim_cols_sql = ",\n            ".join(f"{col} vector({dim})" for dim, col in _DIM_COLUMNS.items())
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS chunks (
                chunk_id TEXT PRIMARY KEY,
                doc_name TEXT NOT NULL,
                section_path TEXT,
                chunk_text TEXT NOT NULL,
                {dim_cols_sql}
            );
            """
        )
    conn.commit()


def upsert_chunk(conn, chunk_id: str, doc_name: str, section_path: str, text: str, embeddings_by_dim: dict[int, list[float]]) -> None:
    columns = ["chunk_id", "doc_name", "section_path", "chunk_text"] + [_DIM_COLUMNS[d] for d in config.TEST_DIMENSIONS]
    placeholders = ", ".join(["%s"] * len(columns))
    update_clause = ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c != "chunk_id")
    values = [chunk_id, doc_name, section_path, text] + [embeddings_by_dim[d] for d in config.TEST_DIMENSIONS]

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO chunks ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT (chunk_id) DO UPDATE SET {update_clause};
            """,
            values,
        )


def nearest_neighbors(conn, dim: int, query_embedding: list[float], top_k: int) -> list[dict]:
    """Real pgvector similarity search: ORDER BY cosine distance (<=>), ascending
    (0 = identical direction). Returns top_k rows with their cosine distance."""
    from pgvector import Vector

    # A bare Python list has no fixed target type until psycopg resolves one from
    # context (e.g. an INSERT into a known `vector` column) -- in a SELECT's WHERE/
    # ORDER BY there's no such context, so it defaults to a Postgres array and pgvector's
    # `<=>` operator has no overload for `vector <=> double precision[]`. Wrapping in
    # pgvector.Vector forces the correct type regardless of context.
    query_vec = Vector(query_embedding)
    column = _DIM_COLUMNS[dim]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT chunk_id, doc_name, section_path, chunk_text, {column} <=> %s AS distance
            FROM chunks
            ORDER BY {column} <=> %s
            LIMIT %s;
            """,
            [query_vec, query_vec, top_k],
        )
        rows = cur.fetchall()
        cols = [d.name for d in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def chunk_count(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks;")
        return cur.fetchone()[0]
