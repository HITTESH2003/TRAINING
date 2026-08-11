# Step-by-step examples

The `db_features/` package next door is written for reuse — shared
connection helpers, functions calling functions — which makes it good for
`run_demos.py` but hard to read start to finish if you're new to this.

These five scripts are the opposite: each one is a **standalone, linear
file**. No imports from other files in this project, no functions calling
functions — just numbered steps, top to bottom. Run any one of them on its
own; you never have to jump between files to understand what's happening.

| Script | What it shows |
|---|---|
| [01_connect_and_view_data.py](./01_connect_and_view_data.py) | Open a connection, look at the table's columns, print real rows |
| [02_embedding_search.py](./02_embedding_search.py) | Embed a question, run a pgvector similarity search, print ranked results |
| [03_metadata_filtered_search.py](./03_metadata_filtered_search.py) | Same search as script 02, restricted to one document with a `WHERE` clause |
| [04_fulltext_search.py](./04_fulltext_search.py) | Postgres's built-in keyword search (`tsvector`), and why it's not the same as embedding search |
| [05_index_and_explain.py](./05_index_and_explain.py) | Create an index, then use `EXPLAIN ANALYZE` to check whether Postgres actually used it |

## Before running any of them

Module 4's Postgres container needs to be up, with chunks already loaded
into it:

```bash
cd "../../4. EMBEDDING AND DATABASE"
docker compose up -d
```

Then, from this folder:

```bash
python 01_connect_and_view_data.py
python 02_embedding_search.py
python 03_metadata_filtered_search.py
python 04_fulltext_search.py
python 05_index_and_explain.py
```

Scripts 02 and 03 load the `nomic-embed-text-v1.5` embedding model (same one
Module 4 used) — first run takes a bit longer while it downloads.

## Where the "real" numbers live

These scripts are for reading the *mechanics* clearly. The actual measured
comparisons — 200,000-row index benchmark, full-text vs. vector precision,
the Excel report — are still produced by `db_features/` + `run_demos.py`,
covered in the main [module README](../README.md).
