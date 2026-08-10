"""Connects to the SAME Postgres container Module 4 already built and
populated -- this module doesn't stand up its own database. Run Module 4's
`docker compose up -d` and `load_and_store.py` first; this module is
entirely about exploring the database that leaves behind, not rebuilding it.
"""

from __future__ import annotations

import os
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent

# Identical to "4. EMBEDDING AND DATABASE/embedding/config.py" -- same
# container, same port, same credentials, on purpose.
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5433"))
PG_USER = os.environ.get("PG_USER", "embedding_student")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "embedding_student")
PG_DATABASE = os.environ.get("PG_DATABASE", "embeddings")

EMBEDDING_MODEL_ID = "nomic-ai/nomic-embed-text-v1.5"
# The chunks table (from Module 4) has columns embedding_768 .. embedding_64;
# demos here default to 256 as a representative middle dimension unless a
# demo has a specific reason to use another one.
DEFAULT_DIM = 256

# Purely synthetic, purely for the index-benchmark demo -- not real chunks,
# not real embeddings, just enough random vectors to make an index scan
# actually beat a sequential scan and be honest about it.
BENCHMARK_TABLE = "benchmark_vectors"
BENCHMARK_ROW_COUNT = 200_000
BENCHMARK_DIM = 256


def pg_dsn() -> str:
    return f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASSWORD} dbname={PG_DATABASE}"
