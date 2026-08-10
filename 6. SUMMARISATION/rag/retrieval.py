"""Embed a question and retrieve the top_k most similar chunks from
Postgres -- the exact same connection, embedding recipe, and pgvector
<=> query pattern verified in Modules 4 and 5, reused here rather than
re-derived.
"""

from __future__ import annotations

from pgvector import Vector

from . import config

_MODEL = None


def connect():
    import psycopg
    from pgvector.psycopg import register_vector

    conn = psycopg.connect(config.pg_dsn())
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()
    register_vector(conn)
    return conn


def require_chunks_table(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chunks');")
        exists = cur.fetchone()[0]
    if not exists:
        raise SystemExit(
            "The `chunks` table doesn't exist yet. Run Module 4 first:\n"
            '  cd "../4. EMBEDDING AND DATABASE" && docker compose up -d\n'
            '  "../1. OCR/.venv/bin/python" load_and_store.py'
        )
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks;")
        return cur.fetchone()[0]


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_embedding_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        device = _resolve_device()
        print(f"  [retrieval] loading {config.EMBEDDING_MODEL_ID} on device: {device}")
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL_ID, trust_remote_code=True, device=device)
    return _MODEL


def embed_query(text: str, dim: int = config.DEFAULT_DIM) -> list[float]:
    """Same task-prefix + layer_norm/slice/renormalize recipe verified in
    Module 4's nomic_embed.py -- duplicated here deliberately, each module
    stays self-contained."""
    import torch.nn.functional as F

    model = _load_embedding_model()
    raw = model.encode([f"search_query: {text}"], convert_to_tensor=True, show_progress_bar=False)
    normed = F.layer_norm(raw, normalized_shape=(raw.shape[-1],))
    truncated = normed[..., :dim]
    return F.normalize(truncated, p=2, dim=-1)[0].tolist()


def retrieve(conn, question: str, top_k: int = config.DEFAULT_TOP_K, dim: int = config.DEFAULT_DIM, doc_name: str | None = None) -> list[dict]:
    query_vec = Vector(embed_query(question, dim))
    column = f"embedding_{dim}"

    where_clause = "WHERE doc_name = %s" if doc_name else ""
    params = [query_vec]
    if doc_name:
        params.append(doc_name)
    params += [query_vec, top_k]

    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT chunk_id, doc_name, section_path, chunk_text, {column} <=> %s AS distance
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
