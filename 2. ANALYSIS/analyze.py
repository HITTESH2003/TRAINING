"""
Module 2: Analysis — validation & reporting over Module 1's OCR output.

For every document Module 1 processed, computes:
  - page count, word count, token count (Qwen3.5-0.8B's own tokenizer), tokens/page
  - images and tables found in the markdown body
  - artifacts detected (logo / signature / stamp_seal counts)
  - low-confidence regions and dropped regions worth a second look
  - native PDF metadata (title, author, creation date)

...and writes it all to one Excel workbook: Summary sheet (one row per
document) + Artifacts / Low Confidence / Dropped Regions detail sheets.

Usage:
  python analyze.py                              # reads ../1. OCR/output, writes ./ocr_analysis_report.xlsx
  python analyze.py --ocr-output some/output/dir  # point at a different Module 1 output folder
  python analyze.py --report custom_report.xlsx   # write elsewhere
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analysis import config, report, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze Module 1 OCR output and write an Excel report")
    parser.add_argument("--ocr-output", type=Path, default=config.DEFAULT_OCR_OUTPUT_DIR, help="Module 1's output/ folder")
    parser.add_argument("--report", type=Path, default=config.DEFAULT_REPORT_PATH, help="where to write the .xlsx report")
    args = parser.parse_args()

    if not args.ocr_output.is_dir():
        sys.exit(f"OCR output folder not found: {args.ocr_output}")

    doc_dirs = stats.discover_documents(args.ocr_output)
    if not doc_dirs:
        sys.exit(f"No completed Module 1 runs found in {args.ocr_output}")

    print(f"Found {len(doc_dirs)} document(s) in {args.ocr_output}")
    results = []
    for doc_dir in doc_dirs:
        print(f"  analyzing {doc_dir.name}...")
        results.append(stats.analyze_document(doc_dir))

    print("Writing report...")
    report.build_report(results, args.report)
    print(f"done -> {args.report}")


if __name__ == "__main__":
    main()
