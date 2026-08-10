# Module 4: Embedding & Database

Takes Module 3's chunks, embeds them with `nomic-embed-text-v1.5`, stores
them in Postgres (pgvector), and runs a real, measured experiment: **how
much does shrinking the embedding dimension actually cost you at retrieval
time?**

Docker is used here only as "the way we run Postgres" -- this module isn't
a Docker course. One `docker compose up -d` and you never think about
Docker again until the next module goes deeper on it.

## Why Nomic specifically

`nomic-embed-text-v1.5` was trained with **Matryoshka Representation
Learning**: it produces a native 768-dimension embedding, but the *first N*
dimensions of that embedding are themselves a valid, meaningful embedding
for any N you choose (768, 512, 256, 128, 64, even smaller). That's exactly
what this module needs to demonstrate "dimension vs. accuracy" honestly --
one model, one set of embeddings, truncated to different sizes, rather than
five different models that aren't really comparable.

## Setup

```bash
cd "4. EMBEDDING AND DATABASE"
docker compose up -d                 # Postgres + pgvector, host port 5433
"../1. OCR/.venv/bin/python" -m pip install -r requirements.txt   # reuses Module 1's venv
```

`docker-compose.yml` maps host port **5433** (not 5432) specifically so this
never collides with a Postgres you might already have running locally.
Credentials are dev-only, in plaintext, in the compose file -- fine for a
local teaching container, not a pattern to carry into anything real.

## Run

```bash
"../1. OCR/.venv/bin/python" load_and_store.py     # embed + store
"../1. OCR/.venv/bin/python" run_experiment.py      # measure
```

`load_and_store.py` reads every `hierarchical.json` chunk from Module 3's
output (18 chunks across the 3 documents), embeds each one once at the
model's native 768 dimensions, truncates that single embedding down to
every dimension in `embedding/config.py`'s `TEST_DIMENSIONS` (768, 512,
256, 128, 64), and stores all five alongside the chunk text in one
Postgres table.

`run_experiment.py` runs 10 hand-written queries (see below) through a
**real pgvector SQL similarity search** -- not numpy, an actual `ORDER BY
embedding <=> query LIMIT k` against the running database -- at each
dimension, and checks where the known-correct chunk landed in the ranking.
Writes `dimension_accuracy_report.xlsx`.

## Getting the truncation right (this is the part people get wrong)

Two details from the model's own card, easy to skip, that silently hurt
retrieval quality if you do:

**1. Task prefixes aren't optional.** Nomic trained this model expecting
`"search_document: "` prepended to everything you store and
`"search_query: "` prepended to everything you search with. Skip it and
the model still produces embeddings -- no error -- they're just measurably
worse. `embedding/nomic_embed.py` applies these automatically.

**2. Truncation is layer_norm → slice → re-normalize, in that order** --
not "L2-normalize then slice," which is a different operation the model
was never trained to support:

```python
embeddings = F.layer_norm(embeddings, normalized_shape=(embeddings.shape[-1],))
embeddings = embeddings[:, :matryoshka_dim]
embeddings = F.normalize(embeddings, p=2, dim=1)
```

This is copied directly from `nomic-ai/nomic-embed-text-v1.5`'s model card,
not derived -- see `embedding/nomic_embed.py::truncate_and_normalize`.

## The database

One table, one row per chunk, one `vector(N)` column per tested dimension
(not five separate tables) -- "same chunk, different dimension" is a
column lookup, not a join:

```sql
CREATE TABLE chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_name TEXT NOT NULL,
    section_path TEXT,
    chunk_text TEXT NOT NULL,
    embedding_768 vector(768),
    embedding_512 vector(512),
    embedding_256 vector(256),
    embedding_128 vector(128),
    embedding_64  vector(64)
);
```

Similarity search uses pgvector's `<=>` cosine-distance operator directly
in SQL (`embedding/db.py::nearest_neighbors`) -- 0 means identical
direction, larger means less similar.

## The 10 queries (`embedding/queries.py`)

Deliberately small and deliberately manual: every `expected_chunk_id` was
picked by a human reading the actual chunk text, so the ground truth is
verifiable by eye, not generated. Each query targets one fact that appears
in exactly one chunk across all 18.

## What we actually measured

```
dim= 768  recall@1=0.70  recall@3=1.00  MRR=0.82  avg_dist_to_correct=0.2645
dim= 512  recall@1=0.70  recall@3=0.90  MRR=0.79  avg_dist_to_correct=0.2671
dim= 256  recall@1=0.70  recall@3=0.90  MRR=0.77  avg_dist_to_correct=0.2527
dim= 128  recall@1=0.70  recall@3=0.90  MRR=0.77  avg_dist_to_correct=0.2253
dim=  64  recall@1=0.70  recall@3=0.90  MRR=0.77  avg_dist_to_correct=0.1915
```

(`recall@k` = fraction of the 10 queries where the correct chunk appeared
in the top k results; MRR = mean reciprocal rank, 1.0 if always ranked
first. Full numbers, including Nomic's own published MTEB benchmarks
across these same dimensions for comparison, belong in the slide deck when
this module gets one.)

**The headline finding is *not* "recall@1 stayed flat at 70%."** It's this
one query, tracked across every dimension in `dimension_accuracy_report.xlsx`'s
`Per-Query Detail` sheet:

| Dimension | "Who signed the regional operations report as Regional Director?" |
|---|---|
| 768 | rank 2 |
| 512 | rank 5 |
| 256 | not in top 5 |
| 128 | not in top 5 |
| 64 | not in top 5 |

Every other query held roughly steady across all five dimensions. This one
-- whose answer is a short, low-information fact ("J. Alvarez, Regional
Director") -- degrades hard and monotonically as dimension shrinks, falling
out of the top 5 entirely below 512 dimensions. The aggregate recall
numbers hide this completely; only the per-query detail shows it.

**The second finding is a trap worth naming explicitly:**
`avg_distance_to_correct` *improves* (gets smaller) as dimension shrinks --
0.2645 at 768 dims down to 0.1915 at 64 dims. That looks like lower
dimensions are "more confident," but they're not: a coarser embedding space
compresses *everything* closer together, correct answers and wrong ones
alike. The ranking metrics (recall@k, MRR) are what actually tell you
whether retrieval quality held up; the raw distance number can improve
while the thing you actually care about gets worse. Don't tune a system by
watching similarity scores go up.

## Why this matters practically

Nomic's own published benchmark shows a small, graceful accuracy drop from
768 → 256 dimensions (MTEB 62.28 → 61.04) -- the pitch for Matryoshka
embeddings is "shrink the vector, keep most of the accuracy, cut storage
and search cost." Our own tiny 18-chunk, 10-query experiment roughly
matches that story in aggregate. But it also shows *why* an aggregate
benchmark number isn't the whole picture: short, specific, low-redundancy
facts (a name, a signature line, a single data point) are the content most
at risk when you compress the embedding space, even when the average
across a whole corpus looks fine. That's a real, generalizable lesson, not
specific to this one document.
