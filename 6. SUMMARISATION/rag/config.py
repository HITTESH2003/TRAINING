"""Connects to the SAME Postgres container Modules 4 and 5 already built and
explored. This module is the payoff: retrieve real chunks from it, then
summarize them with a real small LLM. Run Module 4's docker compose +
load_and_store.py first if you haven't already.
"""

from __future__ import annotations

import os

# Identical to Modules 4 and 5's config.py -- same container, same port.
PG_HOST = os.environ.get("PG_HOST", "localhost")
PG_PORT = int(os.environ.get("PG_PORT", "5433"))
PG_USER = os.environ.get("PG_USER", "embedding_student")
PG_PASSWORD = os.environ.get("PG_PASSWORD", "embedding_student")
PG_DATABASE = os.environ.get("PG_DATABASE", "embeddings")

EMBEDDING_MODEL_ID = "nomic-ai/nomic-embed-text-v1.5"
LLM_MODEL_ID = "Qwen/Qwen3-0.6B"

# Retrieval defaults -- "how many items go into the summary" and "which
# embedding dimension" are exactly the two retrieval knobs this module is
# built to let you feel the effect of.
DEFAULT_TOP_K = 5
DEFAULT_DIM = 256

# Qwen3-0.6B's native context window (see the model card) -- everything this
# module ever assembles (system prompt + retrieved chunks + question) stays
# far under this on our 18-chunk corpus, but the token count is always
# measured and reported so that headroom is visible, not assumed.
MAX_CONTEXT_TOKENS = 32_768

# Qwen3's own recommended sampling parameters -- thinking and non-thinking
# mode are tuned differently on purpose (see the model card), not one
# generic default reused for both.
GENERATION_PRESETS = {
    True: {  # enable_thinking=True
        "temperature": 0.6,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
    },
    False: {  # enable_thinking=False
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.0,
    },
}
DEFAULT_MAX_NEW_TOKENS = 512


def pg_dsn() -> str:
    return f"host={PG_HOST} port={PG_PORT} user={PG_USER} password={PG_PASSWORD} dbname={PG_DATABASE}"
