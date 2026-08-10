"""
Module 3: Chunking — how to split a document into retrieval-sized pieces,
and why the choice of strategy matters, using Module 1's own OCR output.

Runs three chunking strategies over every markdown file in a Module 1 output
folder and writes:
  - output/<doc-name>/<strategy>.json  -- the actual chunks, one file per strategy
  - chunk_comparison_report.xlsx        -- side-by-side stats across every
                                            document x strategy combination

Three genuinely different techniques (see chunking/*.py for the full
reasoning in each file), not three points on one spectrum:

  1. recursive     -- purely mechanical. Given a token size, that's what gets
                      chunked, recursively splitting on paragraph/sentence/word
                      boundaries to respect text, but with no idea what a
                      heading, table, or topic is.
  2. semantic       -- meaning-driven. Embeds each block (Qwen3-Embedding-0.6B)
                      and starts a new chunk wherever similarity to the previous
                      block drops -- a topic shift found in the content itself,
                      with no reference to document structure at all.
  3. hierarchical   -- structure-driven. Headings define a breadcrumb hierarchy,
                      tables/figures are atomic, and chunk boundaries within a
                      section are set by actually reading how much content is
                      there.

Usage:
  python chunk_document.py                                  # every doc in ../1. OCR/output
  python chunk_document.py --ocr-output some/output/dir
  python chunk_document.py --max-tokens 300 --min-tokens 60
  python chunk_document.py --similarity-threshold 0.4        # semantic only
  python chunk_document.py --report custom_report.xlsx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chunking import config
from chunking.compare import build_comparison_report, run_all_strategies, write_json_outputs


def discover_markdown_files(ocr_output_dir: Path) -> list[Path]:
    md_files = []
    for doc_dir in sorted(ocr_output_dir.iterdir()):
        if not doc_dir.is_dir():
            continue
        md_path = doc_dir / f"{doc_dir.name}.md"
        if md_path.exists():
            md_files.append(md_path)
    return md_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Chunk Module 1's OCR output with multiple strategies and compare them")
    parser.add_argument("--ocr-output", type=Path, default=config.DEFAULT_OCR_OUTPUT_DIR, help="Module 1's output/ folder")
    parser.add_argument("--output", type=Path, default=config.DEFAULT_OUTPUT_DIR, help="where to write per-strategy chunk JSON")
    parser.add_argument("--report", type=Path, default=config.MODULE_DIR / "chunk_comparison_report.xlsx", help="where to write the comparison .xlsx")
    parser.add_argument("--max-tokens", type=int, default=config.DEFAULT_MAX_TOKENS, help="target chunk size for recursive/semantic/hierarchical")
    parser.add_argument("--min-tokens", type=int, default=config.DEFAULT_MIN_TOKENS, help="chunks smaller than this get merged (hierarchical only)")
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=config.DEFAULT_SIMILARITY_THRESHOLD,
        help="semantic only: cosine similarity below this between consecutive blocks starts a new chunk",
    )
    args = parser.parse_args()

    if not args.ocr_output.is_dir():
        sys.exit(f"OCR output folder not found: {args.ocr_output}")

    md_files = discover_markdown_files(args.ocr_output)
    if not md_files:
        sys.exit(f"No completed Module 1 runs found in {args.ocr_output}")

    print(f"Found {len(md_files)} document(s) in {args.ocr_output}")

    all_results = {}
    for md_path in md_files:
        doc_name = md_path.stem
        print(f"  chunking {doc_name}...")
        results = run_all_strategies(md_path, max_tokens=args.max_tokens, min_tokens=args.min_tokens, similarity_threshold=args.similarity_threshold)
        for strategy, chunks in results.items():
            print(f"    {strategy:14s} -> {len(chunks)} chunk(s)")
        write_json_outputs(doc_name, results, args.output)
        all_results[doc_name] = results

    print("Writing comparison report...")
    build_comparison_report(all_results, args.report, min_tokens=args.min_tokens)
    print(f"done -> {args.report}")
    print(f"per-strategy chunk JSON -> {args.output}/<doc-name>/<strategy>.json")


if __name__ == "__main__":
    main()
