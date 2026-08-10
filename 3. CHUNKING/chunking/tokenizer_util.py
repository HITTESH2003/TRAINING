"""Token counting via the same tokenizer Module 1's extraction model uses --
consistent with Module 2, so token counts mean the same thing everywhere."""

from __future__ import annotations

from . import config

_TOKENIZER = None


def _load_tokenizer():
    global _TOKENIZER
    if _TOKENIZER is None:
        from transformers import AutoTokenizer

        _TOKENIZER = AutoTokenizer.from_pretrained(config.TOKENIZER_MODEL_ID)
    return _TOKENIZER


def count_tokens(text: str) -> int:
    if not text:
        return 0
    tokenizer = _load_tokenizer()
    return len(tokenizer(text, add_special_tokens=False)["input_ids"])


def get_tokenizer():
    """Exposed for callers that need to encode/decode directly (see
    recursive.py's hard-cut fallback), not just count."""
    return _load_tokenizer()
