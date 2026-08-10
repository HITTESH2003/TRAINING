"""
Module 6 experiment: how does top_k (the number of retrieved chunks handed
to the LLM) actually change the summary?

Fixed question, fixed everything else, top_k swept across a real range,
against Module 4's real 3-document, 18-chunk corpus. For each top_k, this
records which documents got represented in the retrieved set, how many
prompt tokens that costs, and the actual generated answer -- not a
prediction of what should happen.

Usage:
  python run_topk_experiment.py
"""

from __future__ import annotations

import json
from pathlib import Path

from rag import config, llm, prompting, retrieval

QUESTION = "What does this collection of documents cover?"
TOP_K_VALUES = [1, 3, 6, 10, 18]  # 18 = the entire corpus
REPORT_PATH = Path(__file__).resolve().parent / "topk_experiment_report.json"


def run() -> list[dict]:
    conn = retrieval.connect()
    n = retrieval.require_chunks_table(conn)
    print(f"Connected. `chunks` table has {n} rows. Question: {QUESTION!r}\n")

    results = []
    for top_k in TOP_K_VALUES:
        chunks = retrieval.retrieve(conn, QUESTION, top_k=top_k)
        docs_represented = sorted({c["doc_name"] for c in chunks})
        messages = prompting.build_messages(QUESTION, chunks)
        prompt_tokens = llm.count_prompt_tokens(messages, enable_thinking=False)

        print(f"top_k={top_k:2d}  docs_represented={docs_represented}  prompt_tokens={prompt_tokens}")
        gen = llm.generate(messages, enable_thinking=False, max_new_tokens=250)
        print(f"  answer: {gen['answer'][:200]}{'...' if len(gen['answer']) > 200 else ''}")
        print(f"  generation_time_s={gen['generation_time_s']}\n")

        results.append(
            {
                "top_k": top_k,
                "docs_represented": docs_represented,
                "num_docs_represented": len(docs_represented),
                "prompt_tokens": prompt_tokens,
                "context_budget_used_pct": round(100 * prompt_tokens / config.MAX_CONTEXT_TOKENS, 2),
                "answer": gen["answer"],
                "generation_time_s": gen["generation_time_s"],
            }
        )

    conn.close()
    REPORT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {REPORT_PATH}")
    return results


if __name__ == "__main__":
    run()
