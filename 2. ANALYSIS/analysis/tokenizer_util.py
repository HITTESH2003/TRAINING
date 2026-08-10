"""Token counting -- using the same tokenizer the extraction model (Qwen3.5-0.8B)
actually uses, not a word-count approximation. This is 'how you actually check
tokens per page': load the model's tokenizer and count what it produces."""

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
    tokenizer = _load_tokenizer()
    return len(tokenizer(text, add_special_tokens=False)["input_ids"])


def count_words(text: str) -> int:
    return len(text.split())
