"""pgvector ships three distance operators:

  <->   Euclidean / L2 distance
  <=>   cosine distance      (1 - cosine similarity)
  <#>   negative inner product

Tutorials often say "use cosine for normalized embeddings, L2 for others" as
though the choice is consequential. This demo checks that claim empirically
instead of repeating it: our embeddings are L2-normalized (Module 4's
nomic_embed.py ends every embedding with F.normalize), and for unit vectors,
L2² = 2 - 2·cos_similarity -- a strictly monotonic function of cosine
similarity. So all three operators should produce the IDENTICAL ranking on
this data, even though their raw distance numbers look different. Verified
below, not just asserted.
"""

from __future__ import annotations

from pgvector import Vector

from . import config
from .connection import embed_query

OPERATORS = {"l2": "<->", "cosine": "<=>", "inner_product": "<#>"}


def run(conn, query_text: str, dim: int = config.DEFAULT_DIM, top_k: int = 5) -> dict:
    query_vec = Vector(embed_query(query_text, dim))
    column = f"embedding_{dim}"

    rankings = {}
    raw_scores = {}
    for name, op in OPERATORS.items():
        with conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT chunk_id, {column} {op} %s AS score
                FROM chunks
                ORDER BY {column} {op} %s
                LIMIT %s;
                """,
                [query_vec, query_vec, top_k],
            )
            rows = cur.fetchall()
        rankings[name] = [r[0] for r in rows]
        raw_scores[name] = [round(r[1], 4) for r in rows]

    same_ranking = rankings["l2"] == rankings["cosine"] == rankings["inner_product"]

    return {
        "query": query_text,
        "dim": dim,
        "rankings": rankings,
        "raw_scores": raw_scores,
        "same_ranking_across_operators": same_ranking,
    }


def print_result(result: dict) -> None:
    print(f"\nQuery: {result['query']!r}  (dim={result['dim']})")
    for name in OPERATORS:
        print(f"  {name:14s} top-{len(result['rankings'][name])}: {result['rankings'][name]}")
        print(f"  {'':14s} scores: {result['raw_scores'][name]}")
    verdict = "IDENTICAL" if result["same_ranking_across_operators"] else "DIFFERENT"
    print(f"  -> ranking across all three operators: {verdict}")
