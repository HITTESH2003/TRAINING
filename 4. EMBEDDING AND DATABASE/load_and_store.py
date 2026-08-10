"""
Module 4: Embedding & Database — embed Module 3's chunks with nomic-embed-text-v1.5
at multiple dimensions and store all of them in Postgres (pgvector).

One model forward pass per chunk produces the native 768-dim embedding; every
smaller test dimension is a truncation of that same embedding (see
embedding/nomic_embed.py for why this isn't just "slice and hope").

Usage:
  python load_and_store.py
"""

from __future__ import annotations

from embedding import config, corpus, db, nomic_embed


def main() -> None:
    print(f"Loading corpus from {config.DEFAULT_CHUNKING_OUTPUT_DIR} ...")
    chunks = corpus.load_corpus()
    if not chunks:
        raise SystemExit(f"No chunks found in {config.DEFAULT_CHUNKING_OUTPUT_DIR} -- run Module 3 first.")
    print(f"  {len(chunks)} chunk(s) loaded")

    print("Connecting to Postgres ...")
    conn = db.connect()
    db.init_schema(conn)

    print(f"Embedding at dimensions {config.TEST_DIMENSIONS} ...")
    texts = [c["text"] for c in chunks]
    embeddings_by_dim = nomic_embed.embed_documents_all_dims(texts)

    print("Storing in Postgres ...")
    for i, chunk in enumerate(chunks):
        per_chunk_embeddings = {dim: embeddings_by_dim[dim][i] for dim in config.TEST_DIMENSIONS}
        db.upsert_chunk(conn, chunk["chunk_id"], chunk["doc_name"], chunk["section_path"], chunk["text"], per_chunk_embeddings)
    conn.commit()

    total = db.chunk_count(conn)
    conn.close()
    print(f"done -- {total} chunk(s) in the `chunks` table, {len(config.TEST_DIMENSIONS)} embedding columns each")


if __name__ == "__main__":
    main()
