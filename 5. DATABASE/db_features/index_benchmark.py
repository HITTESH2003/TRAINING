"""Does building a vector index actually make search faster -- and does
Postgres even use it?

Module 4's `chunks` table has 18 rows. A sequential scan over 18 rows is
already sub-millisecond; no index changes that, and building one on a table
this size would be a purely theoretical exercise. Rather than fake a
benchmark or just assert "indexes help at scale," this builds a separate,
clearly-synthetic table of BENCHMARK_ROW_COUNT random vectors -- not real
chunks, not real embeddings, labeled as exactly what they are -- specifically
large enough that the difference is real and measurable, and checks with
EXPLAIN ANALYZE whether Postgres's query planner actually chooses to use
the index it's given, rather than assuming it will.
"""

from __future__ import annotations

import time

import numpy as np
from pgvector import Vector

from . import config


def build_benchmark_table(conn, row_count: int = config.BENCHMARK_ROW_COUNT, dim: int = config.BENCHMARK_DIM) -> None:
    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS {config.BENCHMARK_TABLE};")
        cur.execute(f"CREATE TABLE {config.BENCHMARK_TABLE} (id SERIAL PRIMARY KEY, embedding vector({dim}));")
    conn.commit()

    print(f"  generating {row_count} random {dim}-dim vectors ...")
    rng = np.random.default_rng(seed=42)
    batch_size = 5000
    with conn.cursor() as cur:
        for start in range(0, row_count, batch_size):
            n = min(batch_size, row_count - start)
            vecs = rng.normal(size=(n, dim)).astype(np.float32)
            vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)  # unit-normalize, same convention as real embeddings
            with cur.copy(f"COPY {config.BENCHMARK_TABLE} (embedding) FROM STDIN") as copy:
                for vec in vecs:
                    copy.write_row([Vector(vec.tolist())])
    conn.commit()
    print(f"  inserted {row_count} rows into {config.BENCHMARK_TABLE}")


def _explain_and_time(conn, query_vec: Vector, top_k: int) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            f"""
            EXPLAIN (ANALYZE, FORMAT JSON)
            SELECT id FROM {config.BENCHMARK_TABLE}
            ORDER BY embedding <=> %s
            LIMIT %s;
            """,
            [query_vec, top_k],
        )
        plan = cur.fetchone()[0][0]

    node = plan["Plan"]
    scan_type = node["Node Type"]
    # Limit and Sort are wrapper nodes around the actual scan (ORDER BY without
    # an index needs an explicit Sort node) -- descend past both to find what's
    # actually reading the table: Seq Scan or Index Scan.
    while "Plans" in node and scan_type in ("Limit", "Sort"):
        node = node["Plans"][0]
        scan_type = node["Node Type"]

    # real wall-clock timing too, not just the planner's reported time
    start = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id FROM {config.BENCHMARK_TABLE} ORDER BY embedding <=> %s LIMIT %s;",
            [query_vec, top_k],
        )
        cur.fetchall()
    wall_ms = (time.perf_counter() - start) * 1000

    return {
        "scan_type": scan_type,
        "planner_time_ms": round(plan["Planning Time"] + plan["Execution Time"], 2),
        "wall_clock_ms": round(wall_ms, 2),
    }


def benchmark(conn, dim: int = config.BENCHMARK_DIM, top_k: int = 10) -> dict:
    rng = np.random.default_rng(seed=7)
    query_vec = rng.normal(size=dim).astype(np.float32)
    query_vec = Vector((query_vec / np.linalg.norm(query_vec)).tolist())

    results = {}

    with conn.cursor() as cur:
        cur.execute(f"DROP INDEX IF EXISTS {config.BENCHMARK_TABLE}_hnsw_idx;")
        cur.execute(f"DROP INDEX IF EXISTS {config.BENCHMARK_TABLE}_ivfflat_idx;")
    conn.commit()
    results["no_index"] = _explain_and_time(conn, query_vec, top_k)

    print("  building HNSW index ...")
    t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(f"CREATE INDEX {config.BENCHMARK_TABLE}_hnsw_idx ON {config.BENCHMARK_TABLE} USING hnsw (embedding vector_cosine_ops);")
    conn.commit()
    hnsw_build_s = time.perf_counter() - t0
    results["hnsw"] = _explain_and_time(conn, query_vec, top_k)
    results["hnsw"]["build_time_s"] = round(hnsw_build_s, 2)

    with conn.cursor() as cur:
        cur.execute(f"DROP INDEX IF EXISTS {config.BENCHMARK_TABLE}_hnsw_idx;")
    conn.commit()

    print("  building IVFFlat index ...")
    lists = max(1, int(config.BENCHMARK_ROW_COUNT**0.5))  # pgvector's own rule of thumb: rows^0.5 for < 1M rows
    t0 = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(f"CREATE INDEX {config.BENCHMARK_TABLE}_ivfflat_idx ON {config.BENCHMARK_TABLE} USING ivfflat (embedding vector_cosine_ops) WITH (lists = {lists});")
    conn.commit()
    ivfflat_build_s = time.perf_counter() - t0
    results["ivfflat"] = _explain_and_time(conn, query_vec, top_k)
    results["ivfflat"]["build_time_s"] = round(ivfflat_build_s, 2)
    results["ivfflat"]["lists"] = lists

    return results
