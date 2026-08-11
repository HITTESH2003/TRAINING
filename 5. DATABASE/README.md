# Module 5: Database — a deep dive into Postgres + pgvector

This module doesn't build a new database -- it goes deep into the one
Module 4 already built. Same container, same `chunks` table, same 18 real
embedded chunks. If Module 4 hasn't been run yet, none of this works:

```bash
cd "../4. EMBEDDING AND DATABASE"
docker compose up -d
"../1. OCR/.venv/bin/python" load_and_store.py
```

## Why Postgres, specifically

Four features made it the default choice for this whole pipeline, not just
"a place to put vectors":

- **Extensions, not a separate product.** `pgvector` turns on with
  `CREATE EXTENSION vector;` -- vector search lives in the same database as
  everything else, one connection, one transaction model, no second system
  to keep in sync.
- **Real SQL around the vectors.** `WHERE doc_name = ...` combined with
  `ORDER BY embedding <=> ...` is one query, not "search a vector store,
  then filter in application code."
- **More than one kind of search, natively.** Full-text search
  (`tsvector`/`tsquery`) ships with core Postgres -- no extension needed --
  and this module runs it side by side with vector search on the same data.
- **A real, inspectable query planner.** `EXPLAIN ANALYZE` tells you the
  truth about whether an index is actually being used, not just whether you
  created one.

## New to this? Start with `step_by_step/`

[step_by_step/](./step_by_step/) has five standalone scripts — connect and
view data, embedding search, metadata-filtered search, full-text search,
index + `EXPLAIN ANALYZE` — each one linear, no imports between files, no
abstraction to trace through. Read the file top to bottom and that's the
whole thing. This is the easiest place to actually see how the code works.

The rest of this README covers `db_features/` + `run_demos.py`, the
reusable version of the same ideas that produces the real report below.

## Run

```bash
cd "5. DATABASE"
"../1. OCR/.venv/bin/python" run_demos.py
```

Runs all four demos below in order and writes
`database_features_report.xlsx`. The index benchmark builds a 200,000-row
synthetic table and two indexes on it, which takes a couple of minutes;
skip it with `--skip-index-benchmark` if you just want the first three
demos (no report gets written without it, since the report has a sheet per
demo).

## The four demos

### 1. Distance operators (`db_features/operators_demo.py`)

pgvector ships three: `<->` (Euclidean/L2), `<=>` (cosine distance),
`<#>` (negative inner product). Tutorials often say "use cosine for
normalized embeddings" as though the choice is consequential. This demo
checks that empirically instead of repeating it: since Module 4's
embeddings are L2-normalized, and `L2² = 2 − 2·cos_similarity` for unit
vectors, all three operators should produce the **identical ranking** on
this data — verified, not assumed. They do, on all three tested queries;
only the raw score numbers differ.

### 2. Metadata-filtered vector search (`db_features/metadata_search.py`)

Combines a `WHERE doc_name = ...` filter with `ORDER BY embedding <=> ...`
in one query — the real pattern for "find content similar to X, but only
within document Y." Tested several queries against real chunks to find a
case where the filter actually changes the answer (most don't, since the
3-document corpus is topically distinct): **"important developments and
changes"** returns a Federal Register chunk unfiltered, but the correct
NASA chunk when filtered to `nasa_iss_factsheet` — a real example of why
filtering matters, not a hypothetical one.

### 3. Full-text vs. vector search (`db_features/fulltext_search.py`)

Adds a generated `tsvector` column + GIN index, and runs the same queries
through both engines. The result is a clean, complementary-strengths story:

| Query | Full-text | Vector |
|---|---|---|
| `"92 percent"` | finds the right chunk directly | gets it **wrong at rank 1** (right answer is rank 2) |
| `"Houston Texas"` | finds it | finds it |
| `"orbital laboratory"` | finds it | finds it |
| `"how much did border crossings decrease"` (paraphrase) | **no matches at all** | finds it correctly |
| `"an orbiting laboratory where things float"` (paraphrase) | **no matches at all** | finds it correctly |

Full-text search wins on exact terms and numbers; vector search wins on
paraphrase. Neither replaces the other — this is the actual case for
hybrid search, demonstrated rather than asserted.

### 4. Index benchmark (`db_features/index_benchmark.py`)

Module 4's `chunks` table has 18 rows — too small for any index to matter;
Postgres would (correctly) ignore one. So this demo builds a **separate,
clearly-synthetic** table (`benchmark_vectors`, 200,000 random unit vectors,
not real chunks) specifically to make the difference real and measurable,
and checks with `EXPLAIN (ANALYZE, FORMAT JSON)` which scan type Postgres
actually chooses — not just whether an index exists.

Both HNSW and IVFFlat indexes are built and compared against no index at
all. This run's real numbers:

| Method | Scan type (EXPLAIN ANALYZE) | Wall-clock | Index build time |
|---|---|---|---|
| No index | `Gather Merge` (parallel seq scan) | 29.45 ms | — |
| HNSW | `Index Scan` | 1.14 ms | 219.3 s |
| IVFFlat (lists=447) | `Index Scan` | 0.77 ms | 7.5 s |

Both indexes are a real ~25–38x query speedup. But HNSW took roughly **29x
longer to build** than IVFFlat, and IVFFlat also edged out HNSW on query
speed here — not the usual story, where HNSW is normally the
accuracy/recall favorite. Likely explanation: `benchmark_vectors` is
uniformly random with no real semantic cluster structure, which is exactly
what IVFFlat's clustering approach is suited for and doesn't showcase
HNSW's usual advantage. The lesson isn't "IVFFlat wins" — it's that the
right index depends on your actual data and your actual constraints (build
time vs. query time vs. accuracy), not a universal default. Full detail in
`database_features_report.xlsx`'s "Index Benchmark" sheet.

## What's genuinely synthetic here, and why

Everything in demos 1–3 runs against Module 4's real 18 chunks — real
documents, real OCR output, real embeddings. Only demo 4's
`benchmark_vectors` table is synthetic, and it's built that way on purpose:
it exists solely to have enough rows for an index to matter, and is never
presented as anything else.
