"""Reads one Module 1 (OCR) output folder and computes validation stats for it:
page count, word/token counts, images/tables found, artifacts (logo/signature/
stamp_seal) detected, and how many regions need a second look (low-confidence
or dropped by the layout detector)."""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import tokenizer_util

_IMAGE_MARKDOWN_RE = re.compile(r"!\[")
_TABLE_TAG_RE = re.compile(r"<table", re.IGNORECASE)


def discover_documents(ocr_output_dir: Path) -> list[Path]:
    """Returns every subfolder of ocr_output_dir that looks like a completed
    Module 1 run (has both <name>.md and metadata.json)."""
    docs = []
    for entry in sorted(ocr_output_dir.iterdir()):
        if not entry.is_dir():
            continue
        if (entry / f"{entry.name}.md").exists() and (entry / "metadata.json").exists():
            docs.append(entry)
    return docs


def analyze_document(doc_dir: Path) -> dict:
    markdown_text = (doc_dir / f"{doc_dir.name}.md").read_text(encoding="utf-8")
    ocr_metadata = json.loads((doc_dir / "metadata.json").read_text(encoding="utf-8"))

    pdf_meta = ocr_metadata.get("pdf_metadata", {})
    artifacts = ocr_metadata.get("artifacts_detected", [])
    low_confidence = ocr_metadata.get("low_confidence_regions", [])
    dropped = ocr_metadata.get("dropped_regions", [])

    page_count = pdf_meta.get("page_count", 0)
    word_count = tokenizer_util.count_words(markdown_text)
    token_count = tokenizer_util.count_tokens(markdown_text)

    artifact_type_counts: dict[str, int] = {}
    for artifact in artifacts:
        artifact_type_counts[artifact["type"]] = artifact_type_counts.get(artifact["type"], 0) + 1
    known_types = ("logo", "signature", "stamp_seal")

    return {
        "document": doc_dir.name,
        "title": pdf_meta.get("title", ""),
        "author": pdf_meta.get("author", ""),
        "creation_date": pdf_meta.get("creationDate", ""),
        "page_count": page_count,
        "word_count": word_count,
        "token_count": token_count,
        "tokens_per_page": round(token_count / page_count, 1) if page_count else 0,
        "images_in_body": len(_IMAGE_MARKDOWN_RE.findall(markdown_text)),
        "tables_in_body": len(_TABLE_TAG_RE.findall(markdown_text)),
        "logo_count": artifact_type_counts.get("logo", 0),
        "signature_count": artifact_type_counts.get("signature", 0),
        "stamp_seal_count": artifact_type_counts.get("stamp_seal", 0),
        "other_artifact_count": sum(v for k, v in artifact_type_counts.items() if k not in known_types),
        "low_confidence_count": len(low_confidence),
        "dropped_region_count": len(dropped),
        "malformed_table_count": ocr_metadata.get("malformed_table_count", 0),
        "artifacts": artifacts,
        "low_confidence_regions": low_confidence,
        "dropped_regions": dropped,
    }


def analyze_all(ocr_output_dir: Path) -> list[dict]:
    return [analyze_document(d) for d in discover_documents(ocr_output_dir)]
