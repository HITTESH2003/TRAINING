"""
STEP-BY-STEP #3 -- Same embedding search as script 02, but restricted to
one document. Compare this file to 02 side by side: the only real change
is one WHERE clause -- everything else is identical.

Before running: Module 4's Postgres container must be up with chunks in it.
    cd "../../4. EMBEDDING AND DATABASE" && docker compose up -d

Run:
    python 03_metadata_filtered_search.py
"""

import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector
from sentence_transformers import SentenceTransformer
import torch.nn.functional as F

# ── Step 1: connect (identical to script 02) ─────────────────────────
conn = psycopg.connect(host="localhost", port=5433, user="embedding_student",
                        password="embedding_student", dbname="embeddings")
register_vector(conn)
cur = conn.cursor()

# ── Step 2: which document are we restricting the search to? ─────────
# Look at what doc_name values actually exist before picking one.
cur.execute("SELECT DISTINCT doc_name FROM chunks ORDER BY doc_name;")
available_docs = [row[0] for row in cur.fetchall()]
print("Documents in the table:", available_docs)
target_doc = available_docs[0]
print(f"Filtering to: {target_doc!r}\n")

# ── Step 3: load model, embed the question (identical to script 02) ──
print("Loading nomic-embed-text-v1.5 ...")
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

question = "What percentage did illegal border crossings drop by?"
raw = model.encode([f"search_query: {question}"], convert_to_tensor=True)

DIMENSION = 256
normed = F.layer_norm(raw, normalized_shape=(raw.shape[-1],))
truncated = normed[..., :DIMENSION]
query_embedding = F.normalize(truncated, p=2, dim=-1)[0].tolist()
query_vector = Vector(query_embedding)

# ── Step 4: unfiltered search -- searches every document ─────────────
cur.execute(
    """
    SELECT chunk_id, doc_name, embedding_256 <=> %s AS distance
    FROM chunks
    ORDER BY embedding_256 <=> %s
    LIMIT 5;
    """,
    [query_vector, query_vector],
)
print("Unfiltered (searches all documents):")
for chunk_id, doc_name, distance in cur.fetchall():
    print(f"  distance={distance:.4f}  [{doc_name}] {chunk_id}")

# ── Step 5: filtered search -- one extra WHERE clause, nothing else changes
cur.execute(
    """
    SELECT chunk_id, doc_name, embedding_256 <=> %s AS distance
    FROM chunks
    WHERE doc_name = %s
    ORDER BY embedding_256 <=> %s
    LIMIT 5;
    """,
    [query_vector, target_doc, query_vector],
)
print(f"\nFiltered to doc_name = {target_doc!r}:")
for chunk_id, doc_name, distance in cur.fetchall():
    print(f"  distance={distance:.4f}  [{doc_name}] {chunk_id}")

print(
    "\nNote: filtering can raise the top distance (fewer candidates to choose\n"
    "from) but it guarantees every result actually comes from the document\n"
    "you asked about -- useful when a user says 'search only in report X.'"
)

cur.close()
conn.close()
