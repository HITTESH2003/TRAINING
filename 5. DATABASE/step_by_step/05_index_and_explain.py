"""
STEP-BY-STEP #5 -- Does creating an index actually make Postgres use it?
Prove it with EXPLAIN ANALYZE instead of assuming it.

Before running: Module 4's Postgres container must be up with chunks in it.
    cd "../../4. EMBEDDING AND DATABASE" && docker compose up -d

Run:
    python 05_index_and_explain.py
"""

import psycopg
from pgvector.psycopg import register_vector

conn = psycopg.connect(host="localhost", port=5433, user="embedding_student",
                        password="embedding_student", dbname="embeddings")
register_vector(conn)
cur = conn.cursor()

# ── Step 1: how many rows are we working with? ───────────────────────
cur.execute("SELECT COUNT(*) FROM chunks;")
row_count = cur.fetchone()[0]
print(f"chunks table has {row_count} rows.")

# ── Step 2: create an HNSW index on the 256-dim column ────────────────
# (IF NOT EXISTS makes this safe to run more than once)
print("\nCreating an HNSW index on embedding_256 ...")
cur.execute("""
    CREATE INDEX IF NOT EXISTS chunks_hnsw_256_idx
    ON chunks USING hnsw (embedding_256 vector_cosine_ops);
""")
conn.commit()
print("Done.")

# ── Step 3: get a real vector to search with -- just reuse one chunk's own
# embedding, so this script doesn't need to load an embedding model at all.
cur.execute("SELECT embedding_256 FROM chunks LIMIT 1;")
example_vector = cur.fetchone()[0]

# ── Step 4: ask Postgres to EXPLAIN ANALYZE the query -- this shows what
# the query planner actually chose to do, not just what indexes exist.
cur.execute(
    """
    EXPLAIN ANALYZE
    SELECT chunk_id FROM chunks
    ORDER BY embedding_256 <=> %s
    LIMIT 5;
    """,
    [example_vector],
)
print("\nEXPLAIN ANALYZE output:\n")
plan_lines = [row[0] for row in cur.fetchall()]
for line in plan_lines:
    print(" ", line)

# ── Step 5: which scan node did Postgres actually pick? Skip past the
# "Limit" / "Sort" wrapper lines to find the real scan underneath.
scan_line = next(line for line in plan_lines if "Scan" in line)
used_index = "Index Scan" in scan_line
print(f"\nActual scan used: {scan_line.strip()}")
print("=> " + ("Index Scan (the index was used)" if used_index else "Seq Scan (the index was IGNORED)"))
print(
    f"\nOn a {row_count}-row table, Postgres almost always picks a Seq Scan --\n"
    "scanning everything directly is cheaper than the overhead of consulting\n"
    "an index when there's this little data. The index isn't wrong to exist;\n"
    "Postgres is just right not to bother using it here.\n\n"
    "See db_features/index_benchmark.py for the same test at 200,000 rows,\n"
    "where a real workload makes the index the clear winner (see README.md\n"
    "for the module's actual measured numbers: ~1.14ms indexed vs ~29ms\n"
    "unindexed)."
)

cur.close()
conn.close()
