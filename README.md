# How to Build Your First Chatbot

A 6-module teaching series, built end to end with real documents, real
models, and real measured results at every step — not toy examples.

The pipeline: a raw PDF becomes classified regions, becomes validated
markdown, becomes retrieval-sized chunks, becomes embeddings stored in
Postgres, becomes a searchable database, becomes a real answer from a real
small LLM — with a Streamlit UI on top.

## Modules

| # | Module | What it covers |
|---|---|---|
| 1 | [OCR](./1.%20OCR/) | PDF → classified regions → structured markdown, using a doc-layout model + a small vision-language model (Qwen3.5-0.8B) |
| 2 | [Analysis](./2.%20ANALYSIS/) | Validating what OCR actually extracted — token counts, confidence flags, artifact tracking |
| 3 | [Chunking](./3.%20CHUNKING/) | Three genuinely different chunking strategies — recursive, semantic, hierarchical — compared on the same real documents |
| 4 | [Embedding & Database](./4.%20EMBEDDING%20AND%20DATABASE/) | Embedding chunks with nomic-embed-text-v1.5 (Matryoshka dimensions) and storing them in Postgres + pgvector, via Docker |
| 5 | [Database Deep Dive](./5.%20DATABASE/) | Distance operators, metadata filtering, full-text vs. vector search, and a real HNSW/IVFFlat index benchmark |
| 6 | [Summarization](./6.%20SUMMARISATION/) | Retrieval + Qwen3-0.6B summarization, with a Streamlit frontend and a measured top_k experiment |

Each module has its own README with setup instructions, a `make_slides.py`
that builds that module's slide deck from its own real output, and — where
applicable — the actual generated reports/decks committed alongside the
code.

## Running any module

One shared virtual environment covers all 6 modules — every package every
module needs lives in the single root [requirements.txt](./requirements.txt),
so there's one install, not six.

**The venv lives inside `1. OCR/`, not at the repo root.** Create it there
specifically — `transformers>=5.2` (needed from Module 1 onward) requires
Python 3.10+, and on macOS a bare `python3 -m venv` elsewhere on your
`PATH` can silently pick up an old system Python (3.8) that fails this
`pip install` with a confusing "no matching distribution" error instead of
a clear version complaint.

```bash
cd "1. OCR"
python3 -m venv .venv && source .venv/bin/activate
python --version              # confirm this actually says 3.10+
pip install -r ../requirements.txt
```

Every later module then reuses this same venv — either `source
"1. OCR/.venv/bin/activate"` first, or invoke it directly:
`"1. OCR/.venv/bin/python" script.py`. Each module's own README covers
what else is specific to that module (e.g. Docker + Postgres from Module 4
onward).

`.venv/` is intentionally excluded from this repository (see
`.gitignore`) — it's several GB and fully reproducible from
`requirements.txt`.
