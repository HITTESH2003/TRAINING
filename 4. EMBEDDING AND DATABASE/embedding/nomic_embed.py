"""Embeddings via nomic-embed-text-v1.5, with correct Matryoshka dimension
truncation -- this is the exact procedure from the model's own card
(huggingface.co/nomic-ai/nomic-embed-text-v1.5), not a guess:

    embeddings = F.layer_norm(embeddings, normalized_shape=(embeddings.shape[1],))
    embeddings = embeddings[:, :matryoshka_dim]
    embeddings = F.normalize(embeddings, p=2, dim=1)

Two details that are easy to get wrong and silently hurt retrieval quality:

1. Task prefixes are required, not optional. Nomic trained this model to
   expect "search_document: " on everything you store and "search_query: "
   on everything you search with -- get this backwards or skip it and the
   embeddings still "work" (no error), they're just measurably worse.

2. Truncation is layer_norm -> slice -> L2-normalize, in that order. Slicing
   a plain L2-normalized 768-dim vector to N dims and renormalizing is NOT
   the same operation and was not what the model was trained for -- the
   layer_norm step first is what makes each nested prefix a meaningful
   embedding on its own, which is the entire point of Matryoshka training.

The model is loaded once at full 768 dimensions; every smaller test
dimension in config.TEST_DIMENSIONS is produced by truncating that same
raw embedding, not by re-running the model -- one forward pass covers every
dimension we test.
"""

from __future__ import annotations

from . import config

_MODEL = None


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        device = _resolve_device()
        print(f"  [nomic_embed] loading {config.EMBEDDING_MODEL_ID} on device: {device}")
        _MODEL = SentenceTransformer(config.EMBEDDING_MODEL_ID, trust_remote_code=True, device=device)
    return _MODEL


def _raw_embed(prefixed_texts: list[str]):
    """Returns raw (un-normalized) embeddings at the model's native 768 dims."""
    model = _load()
    return model.encode(prefixed_texts, convert_to_tensor=True, show_progress_bar=False)


def truncate_and_normalize(raw_embeddings, dim: int):
    """The exact 3-step procedure from the model card: layer_norm, slice, L2-normalize."""
    import torch.nn.functional as F

    embeddings = F.layer_norm(raw_embeddings, normalized_shape=(raw_embeddings.shape[-1],))
    embeddings = embeddings[..., :dim]
    embeddings = F.normalize(embeddings, p=2, dim=-1)
    return embeddings


def embed_documents_all_dims(texts: list[str]) -> dict[int, list[list[float]]]:
    """One forward pass at 768 dims, truncated down to every dimension in
    config.TEST_DIMENSIONS. Returns {dim: [[...], [...], ...]} aligned to texts."""
    prefixed = [f"search_document: {t}" for t in texts]
    raw = _raw_embed(prefixed)
    return {dim: truncate_and_normalize(raw, dim).tolist() for dim in config.TEST_DIMENSIONS}


def embed_query_all_dims(text: str) -> dict[int, list[float]]:
    raw = _raw_embed([f"search_query: {text}"])
    return {dim: truncate_and_normalize(raw, dim)[0].tolist() for dim in config.TEST_DIMENSIONS}
