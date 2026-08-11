"""
STEP-BY-STEP #1 -- Connect to Postgres and look at real data.

No functions, no imports from other files in this project -- every step
happens top to bottom in this one file, in order, so it's obvious what's
happening at each line.

Before running: Module 4's Postgres container must be up and have chunks in it.
    cd "../../4. EMBEDDING AND DATABASE" && docker compose up -d

Run:
    python 01_connect_and_view_data.py
"""

import psycopg

# ── Step 1: connection details ──────────────────────────────────────────
# Same container Module 4 built. Host port 5433 (not 5432) so it never
# collides with a Postgres you might already have running locally.
HOST = "localhost"
PORT = 5433
USER = "embedding_student"
PASSWORD = "embedding_student"
DBNAME = "embeddings"

# ── Step 2: open the connection ─────────────────────────────────────────
conn = psycopg.connect(host=HOST, port=PORT, user=USER, password=PASSWORD, dbname=DBNAME)
print(f"Connected to '{DBNAME}' on {HOST}:{PORT}.\n")

# ── Step 3: open a cursor -- this is the object that sends SQL and reads results back
cur = conn.cursor()

# ── Step 4: how many rows are actually in the table? ────────────────────
cur.execute("SELECT COUNT(*) FROM chunks;")
row_count = cur.fetchone()[0]
print(f"chunks table has {row_count} rows.\n")

# ── Step 5: look at the table's own structure, straight from Postgres ───
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'chunks'
    ORDER BY ordinal_position;
""")
print("Columns in 'chunks':")
for column_name, data_type in cur.fetchall():
    print(f"  {column_name:<16} {data_type}")

# ── Step 6: pull a handful of real rows and print them ───────────────────
cur.execute("""
    SELECT chunk_id, doc_name, section_path, chunk_text
    FROM chunks
    ORDER BY chunk_id
    LIMIT 5;
""")
print("\nFirst 5 rows:\n")
for chunk_id, doc_name, section_path, chunk_text in cur.fetchall():
    preview = chunk_text[:80].replace("\n", " ")
    print(f"  [{chunk_id}] {doc_name} | {section_path}")
    print(f"    \"{preview}...\"\n")

# ── Step 7: always close what you open ───────────────────────────────────
cur.close()
conn.close()
print("Connection closed.")
