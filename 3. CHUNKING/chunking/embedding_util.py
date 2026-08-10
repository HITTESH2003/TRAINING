"""Sentence/paragraph embeddings via Qwen3-Embedding-0.6B -- used only by
semantic.py, to measure how similar consecutive blocks are and detect where
the topic shifts. Same model family as the rest of this pipeline
(Qwen3.5-0.8B for OCR extraction), loaded through plain `transformers` with
no new dependency.

Embeddings are L2-normalized on the way out, so cosine similarity between
two of them is just a dot product -- see cosine_similarity() below.
"""

from __future__ import annotations

from . import config

_TOKENIZER = None
_MODEL = None
_DEVICE = None


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load():
    global _TOKENIZER, _MODEL, _DEVICE
    if _MODEL is None:
        from transformers import AutoModel, AutoTokenizer

        _DEVICE = _resolve_device()
        print(f"  [embedding_util] loading {config.EMBEDDING_MODEL_ID} on device: {_DEVICE}")
        _TOKENIZER = AutoTokenizer.from_pretrained(config.EMBEDDING_MODEL_ID, padding_side="left")
        _MODEL = AutoModel.from_pretrained(config.EMBEDDING_MODEL_ID).to(_DEVICE)
        _MODEL.eval()
    return _TOKENIZER, _MODEL


def _last_token_pool(last_hidden_states, attention_mask):
    # Qwen3-Embedding's documented pooling: with left-padding (set above),
    # the last real token of every sequence is simply the last position.
    return last_hidden_states[:, -1]


def embed_text(text: str):
    """Returns a single L2-normalized embedding vector (torch tensor) for text."""
    import torch
    import torch.nn.functional as F

    tokenizer, model = _load()
    inputs = tokenizer([text], padding=True, truncation=True, max_length=1024, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model(**inputs)
    embedding = _last_token_pool(outputs.last_hidden_state, inputs["attention_mask"])
    embedding = F.normalize(embedding, p=2, dim=1)
    return embedding[0]


def cosine_similarity(a, b) -> float:
    return float((a * b).sum())
