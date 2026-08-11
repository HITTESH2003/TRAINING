"""
STEP-BY-STEP #4 -- Postgres's built-in full-text (keyword) search, and how
it differs from embedding search. No embedding model needed here -- this
is plain SQL text search, Postgres has had it for decades.

Before running: Module 4's Postgres container must be up with chunks in it.
    cd "../../4. EMBEDDING AND DATABASE" && docker compose up -d

Run:
    python 04_fulltext_search.py
"""

import psycopg

conn = psycopg.connect(host="localhost", port=5433, user="embedding_student",
                        password="embedding_student", dbname="embeddings")
cur = conn.cursor()

# ── Step 1: add a full-text search column, if it doesn't exist yet ───
# tsvector is Postgres's "text broken into searchable lexemes" type.
# GENERATED ... STORED means Postgres keeps it in sync automatically
# whenever chunk_text changes -- we never write to it directly.
cur.execute("""
    ALTER TABLE chunks
    ADD COLUMN IF NOT EXISTS chunk_text_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED;
""")
conn.commit()

# ── Step 2: index it, so search doesn't have to scan every row's text ─
cur.execute("""
    CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING GIN (chunk_text_tsv);
""")
conn.commit()
print("Full-text column + index ready.\n")

# ── Step 3: the search term -- plain keywords, not a natural question ─
search_term = "border crossings"

# ── Step 4: run the full-text search ──────────────────────────────────
# websearch_to_tsquery understands normal search syntax (quotes, "-word", etc).
# ts_rank scores how well each row matches -- higher is better (opposite of
# the embedding distance in scripts 02/03, where lower is better).
cur.execute(
    """
    SELECT chunk_id, doc_name,
           ts_rank(chunk_text_tsv, websearch_to_tsquery('english', %s)) AS rank
    FROM chunks
    WHERE chunk_text_tsv @@ websearch_to_tsquery('english', %s)
    ORDER BY rank DESC
    LIMIT 5;
    """,
    [search_term, search_term],
)
print(f"Full-text search for {search_term!r}:\n")
rows = cur.fetchall()
if not rows:
    print("  (no matches -- full-text search needs the exact words to appear)")
for chunk_id, doc_name, rank in rows:
    print(f"  rank={rank:.4f}  [{doc_name}] {chunk_id}")

print(
    "\nFull-text search finds rows containing the literal words. It won't\n"
    "find a chunk about 'illegal immigration falling' for a search on\n"
    "'border crossings' unless those words are actually present -- that's\n"
    "the gap embedding search (scripts 02/03) closes, and why real systems\n"
    "often combine both (see db_features/fulltext_search.py for that comparison)."
)

cur.close()
conn.close()
