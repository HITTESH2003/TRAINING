# Module 6: Summarization — retrieval + a real small LLM, with a UI

This is where the series' pieces actually come together: a question goes
in, Module 4's Postgres/pgvector database gets searched, and `Qwen3-0.6B`
turns the retrieved chunks into an answer. A Streamlit app makes every
retrieval and generation parameter a visible control instead of a buried
constant, because the point of this module is *how those parameters change
the output*, not just that a working demo exists.

Requires Module 4's Postgres container running with data loaded:

```bash
cd "../4. EMBEDDING AND DATABASE"
docker compose up -d
"../1. OCR/.venv/bin/python" load_and_store.py
```

## Setup

```bash
cd "6. SUMMARISATION"
"../1. OCR/.venv/bin/python" -m pip install -r requirements.txt   # just streamlit; everything else is already in the shared venv
```

## Run

```bash
"../1. OCR/.venv/bin/python" -m streamlit run app.py
```

Or run the measured experiment without the UI:

```bash
"../1. OCR/.venv/bin/python" run_topk_experiment.py
```

## The model: Qwen3-0.6B

A real instruction-tuned LLM, not an embedding or vision model this time —
0.6B parameters, 32,768-token native context window. Two model-config
details from its own card that this module gets right on purpose, because
getting them wrong doesn't error, it just quietly produces worse answers:

**`enable_thinking`** — Qwen3 models can emit a `<think>...</think>`
reasoning block before the actual answer. It's set when the prompt is
built (`apply_chat_template(..., enable_thinking=...)`), not parsed after
the fact — toggling it changes what the model is *asked* to produce.
Thinking content is separated from the answer using the model card's own
method: find token id `151668` (`</think>`) in the generated ids and split
there (`rag/llm.py::generate`), not a string search on decoded text.

**Sampling parameters differ by mode, officially** — not one generic
temperature reused for both:

| | temperature | top_p | top_k |
|---|---|---|---|
| Thinking mode | 0.6 | 0.95 | 20 |
| Non-thinking mode | 0.7 | 0.8 | 20 |

`rag/config.py::GENERATION_PRESETS` encodes exactly this, keyed by
`enable_thinking`, and the app shows you which preset is active.

## The four parameters this module is actually about

- **`top_k`** — how many retrieved chunks go into the prompt
- **embedding dimension** — same Matryoshka truncation from Module 4, reused here
- **`enable_thinking`** — changes both the sampling preset and whether a reasoning trace gets generated
- **`max_new_tokens`** — the hard cap on how long an answer can get

All four are sliders/toggles in the app, not hardcoded.

## What we actually measured: `run_topk_experiment.py`

Fixed question — *"What does this collection of documents cover?"* — top_k
swept from 1 to the entire 18-chunk corpus, against the real 3-document
corpus from Modules 1–4. Real results:

| top_k | Documents represented | Prompt tokens | Generation time |
|---|---|---|---|
| 1 | federal_register only | 245 | 2.9 s |
| 3 | federal_register, nasa | 516 | 2.2 s |
| 6 | federal_register, nasa | 1044 | 3.6 s |
| 10 | **all 3** | 1560 | 51.4 s |
| 18 (everything) | all 3 | 2712 | 7.4 s |

**The headline finding**: `synthetic_sample` doesn't appear in the answer
at all until `top_k=10` — more than half the entire corpus. It's not a bug;
that document's table- and chart-heavy chunks are genuinely further in
embedding space from a broad, prose-style question like this one than the
other two documents' chunks are. A low top_k doesn't just retrieve less —
it can silently drop an entire document from the answer with no error or
warning, which is exactly the kind of thing you'd never notice without
measuring it.

**The generation-time spike explains itself, once you look**: 51.4 seconds
at `top_k=10` looks like an anomaly next to 2–8 seconds everywhere else —
until you check the actual output. At `top_k=10`, the model chose to write
a longer, 5-part itemized answer (long enough to hit the 250-token cap and
get cut off mid-sentence) instead of the 1–3 sentence answers it gave at
every other setting. More retrieved context didn't just change *what* got
covered — it changed the *shape* of the answer the model chose to write.
Context budget stayed trivial throughout (0.75%–8.28% of the 32,768-token
window) — this corpus is far too small to ever stress it, but the
percentage is computed and shown every time, not assumed safe.

**A real model quirk, not hidden**: in 2 of these 5 runs (non-thinking
mode), a stray non-English character or garbled word leaked into an
otherwise-clean English answer (`"...southern border d̯."`,
`"NASA ResearchGrammar"`). This is a real, repeatable small-model failure
mode — worth knowing before trusting a 0.6B model's output unsupervised in
anything user-facing.

## The prompt, actually shown

`rag/prompting.py` builds a system instruction + numbered, source-attributed
context blocks + the question — and the Streamlit app shows this exact
assembled text in an expander, not a description of it. If an answer looks
wrong, the first thing to check is what the model actually saw, not what
you assume it saw.

## What's real here vs. Module 4/5's synthetic pieces

Everything in this module runs against Module 4's real 18 chunks and real
stored embeddings — no synthetic filler data this time. The only thing
that varies run to run is the LLM's own sampling (`do_sample=True`, per
Qwen3's recommended presets), so exact wording will differ slightly if you
re-run `run_topk_experiment.py`; the document-coverage pattern and the
overall shape of the finding should not.
