"""Connection helper (same pattern as Module 4's embedding/db.py::connect())
plus a query-embedding helper so search demos can embed new text on the fly
without re-embedding anything Module 4 already stored.
"""

from __future__ import annotations

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
    """Fails loudly and helpfully if Module 4 hasn't been run yet."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'chunks');"
        )
        exists = cur.fetchone()[0]
    if not exists:
        raise SystemExit(
            "The `chunks` table doesn't exist yet. Run Module 4 first:\n"
            '  cd "../4. EMBEDDING AND DATABASE" && docker compose up -d\n'
            '  "../1. OCR/.venv/bin/python" load_and_store.py'
        )
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM chunks;")
        count = cur.fetchone()[0]
    if count == 0:
        raise SystemExit("The `chunks` table exists but is empty -- run Module 4's load_and_store.py first.")
    return count


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        device = _resolve_device()
        print(f"  [connection] loading {config.EMBEDDING_MODEL_ID} on device: {device}")
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL_ID, trust_remote_code=True, device=device)
    return _MODEL


def embed_query(text: str, dim: int = config.DEFAULT_DIM) -> list[float]:
    """Same task-prefix + layer_norm/slice/renormalize recipe as Module 4's
    nomic_embed.py -- duplicated here deliberately (each module stays
    self-contained), not re-derived."""
    import torch.nn.functional as F

    model = _load_model()
    raw = model.encode([f"search_query: {text}"], convert_to_tensor=True, show_progress_bar=False)
    normed = F.layer_norm(raw, normalized_shape=(raw.shape[-1],))
    truncated = normed[..., :dim]
    return F.normalize(truncated, p=2, dim=-1)[0].tolist()
