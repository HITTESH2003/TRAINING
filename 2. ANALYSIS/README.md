# Module 2: Analysis — validation & reporting over Module 1's OCR output

After Module 1 (`1. OCR/`) turns PDFs into markdown + `metadata.json`, this
module reads all of that output and produces one Excel workbook: a
per-document summary plus detail sheets for anything worth a second look.

## Folder layout

```
2. ANALYSIS/
  analysis/        the analysis code, one file per concern
    stats.py         reads a Module 1 output folder, computes stats for it
    tokenizer_util.py  token/word counting
    report.py         builds the Excel workbook
    config.py          default paths
  analyze.py       CLI entrypoint
```

## Setup

This module reuses Module 1's virtual environment rather than installing its
own multi-GB copy of torch/transformers -- it needs the exact same tokenizer
(Qwen3.5-0.8B's) to count tokens the way the extraction model actually saw
them, and that's already sitting in `1. OCR/.venv`. Everything this module
needs (just `openpyxl` on top of Module 1's packages) is already covered by
the root [requirements.txt](../requirements.txt) — if you installed that,
there's nothing more to do here.

## Run

```bash
cd "2. ANALYSIS"
"../1. OCR/.venv/bin/python" analyze.py
```

That reads every completed run in `../1. OCR/output/` and writes
`ocr_analysis_report.xlsx` right here in this folder. Options:

```bash
python analyze.py --ocr-output some/other/output/dir
python analyze.py --report custom_report.xlsx
```

(Run Module 1 first if `1. OCR/output/` is empty -- there's nothing to
analyze until at least one PDF has been processed.)

## What "a document" means here

A subfolder of `1. OCR/output/` counts as analyzable if it has both
`<name>.md` and `metadata.json` -- i.e. Module 1 actually finished on it.
Partial/interrupted runs are silently skipped.

## What's in the report

**Summary sheet** — one row per document:

| Column | Where it comes from |
|---|---|
| `page_count` | Module 1's `metadata.json` → `pdf_metadata.page_count` |
| `word_count` | `len(markdown_text.split())` |
| `token_count` | Qwen3.5-0.8B's own tokenizer run over the markdown -- **this is "how you actually check tokens per page"**: load the same tokenizer the extraction model used (`transformers.AutoTokenizer`), not a word-count guess. Word count and token count are reported side by side deliberately, so the gap between them is visible. |
| `tokens_per_page` | `token_count / page_count` |
| `images_in_body` / `tables_in_body` | counted directly from the markdown (`![...]` and `<table` occurrences) |
| `logo_count` / `signature_count` / `stamp_seal_count` / `other_artifact_count` | tallied from `metadata.json` → `artifacts_detected` |
| `low_confidence_count` | size of `metadata.json` → `low_confidence_regions` |
| `dropped_region_count` | size of `metadata.json` → `dropped_regions` (see Module 1's README -- this includes anything the layout detector classified as `abandon`, including misclassified artifacts like logos) |
| `malformed_table_count` | from `metadata.json` |
| `title` / `author` / `creation_date` | native PDF metadata, blank if the PDF didn't set them |

**Artifacts Detail** — one row per detected logo/signature/stamp_seal, with its page, description, and bounding box.

**Low Confidence Regions** — one row per region the layout detector wasn't sure about, worth a manual check.

**Dropped Regions** — one row per region excluded from the markdown body (headers/footers, but also anything misclassified as `abandon`). Cross-reference bounding boxes here against `1. OCR/output/<doc>/annotated/` to see exactly what got dropped and why.

## A validation habit worth teaching here

`tokens_per_page` varies a lot by document type -- a dense legal proclamation
runs ~500 tokens/page in this sample set, a plain-text fact sheet runs
~250. There's no universal "correct" number, but a document whose
`tokens_per_page` is wildly out of line with similar documents (much lower
-- possible missed content; much higher -- possible garbled/repeated OCR
output) is exactly the kind of signal this sheet exists to surface at a
glance, across many documents, without opening each markdown file by hand.
