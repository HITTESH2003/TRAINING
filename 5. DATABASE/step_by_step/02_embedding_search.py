"""
STEP-BY-STEP #2 -- Turn a question into a vector, ask Postgres for the
closest chunks. This is the core of retrieval: same idea Module 6's
Streamlit app uses, stripped down to one linear script.

Before running: Module 4's Postgres container must be up with chunks in it.
    cd "../../4. EMBEDDING AND DATABASE" && docker compose up -d

Run:
    python 02_embedding_search.py
"""

import psycopg
from pgvector.psycopg import register_vector
from pgvector import Vector
from sentence_transformers import SentenceTransformer
import torch.nn.functional as F

# ── Step 1: connect ───────────────────────────────────────────────────
conn = psycopg.connect(host="localhost", port=5433, user="embedding_student",
                        password="embedding_student", dbname="embeddings")

# psycopg has no built-in idea how to send a Python list as Postgres's
# `vector` type -- register_vector teaches it that, for THIS connection.
register_vector(conn)
cur = conn.cursor()

# ── Step 2: load the same embedding model Module 4 used to embed the chunks
# (must match, or the query vector and the stored vectors live in different
# spaces and distances become meaningless)
print("Loading nomic-embed-text-v1.5 ...")
model = SentenceTransformer("nomic-ai/nomic-embed-text-v1.5", trust_remote_code=True)

# ── Step 3: the question ─────────────────────────────────────────────
question = "What percentage did illegal border crossings drop by?"

# ── Step 4: embed it. Nomic requires a "search_query: " prefix on questions
# and a different "search_document: " prefix on the text being searched --
# the chunks in the table were embedded with the document prefix.
raw = model.encode([f"search_query: {question}"], convert_to_tensor=True)

# ── Step 5: Nomic's Matryoshka truncation recipe (see Module 4's README).
# The model outputs 768 numbers natively; we keep the first 256 of them and
# re-normalize, matching the embedding_256 column in the chunks table.
DIMENSION = 256
normed = F.layer_norm(raw, normalized_shape=(raw.shape[-1],))
truncated = normed[..., :DIMENSION]
query_embedding = F.normalize(truncated, p=2, dim=-1)[0].tolist()

# ── Step 6: ask Postgres for the 5 closest chunks. <=> is pgvector's cosine
# distance operator -- 0 means identical direction, bigger means further apart.
query_vector = Vector(query_embedding)
cur.execute(
    """
    SELECT chunk_id, doc_name, chunk_text, embedding_256 <=> %s AS distance
    FROM chunks
    ORDER BY embedding_256 <=> %s
    LIMIT 5;
    """,
    [query_vector, query_vector],
)

# ── Step 7: print results, closest first ─────────────────────────────
print(f"\nQuestion: {question!r}\n")
for chunk_id, doc_name, chunk_text, distance in cur.fetchall():
    preview = chunk_text[:100].replace("\n", " ")
    print(f"  distance={distance:.4f}  [{doc_name}] {chunk_id}")
    print(f"    \"{preview}...\"\n")

cur.close()
conn.close()
