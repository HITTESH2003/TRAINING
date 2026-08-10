from __future__ import annotations

from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OCR_OUTPUT_DIR = MODULE_DIR.parent / "1. OCR" / "output"
DEFAULT_OUTPUT_DIR = MODULE_DIR / "output"

# Same model as Modules 1 and 2 -- token counts should be consistent across
# the whole pipeline, not a different approximation in every module.
TOKENIZER_MODEL_ID = "Qwen/Qwen3.5-0.8B"

# Same model family as the rest of the pipeline (Qwen3.5-0.8B for OCR) --
# used only by semantic.py to embed blocks and detect topic shifts. Works via
# plain transformers, no new dependency.
EMBEDDING_MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"

# Target chunk size for the size-aware strategies (recursive, hierarchical,
# and as an upper cap for semantic).
DEFAULT_MAX_TOKENS = 200
# Below this, a trailing chunk gets merged into its neighbor instead of
# standing alone as a near-empty fragment.
DEFAULT_MIN_TOKENS = 40
# Cosine similarity below this between consecutive blocks (embeddings are
# L2-normalized, so cosine similarity is just a dot product) is treated as a
# topic shift -- semantic.py starts a new chunk there. Tune per document type;
# see semantic.py's docstring for why 0.5 is a starting point, not a law.
DEFAULT_SIMILARITY_THRESHOLD = 0.5
