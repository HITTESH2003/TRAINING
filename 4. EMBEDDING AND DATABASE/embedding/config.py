from __future__ import annotations

import os
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CHUNKING_OUTPUT_DIR = MODULE_DIR.parent / "3. CHUNKING" / "output"

# Nomic's own Matryoshka benchmark points (see README) -- testing the same
# dimensions makes our own measured numbers directly comparable to Nomic's
# published ones, not an arbitrary set we picked.
TEST_DIMENSIONS = [768, 512, 256, 128, 64]
NATIVE_DIMENSION = 768

EMBEDDING_MODEL_ID = "nomic-ai/nomic-embed-text-v1.5"

# docker-compose.yml maps host 5433 -> container 5432 deliberately, so this
# never collides with a Postgres a student might already have running locally.
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5433"))
PG_USER = os.environ.get("PG_USER", "embedding_student")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "embedding_student")
PG_DATABASE = os.environ.get("PG_DATABASE", "embeddings")


def pg_dsn() -> str:
    return f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASSWORD} dbname={PG_DATABASE}"
