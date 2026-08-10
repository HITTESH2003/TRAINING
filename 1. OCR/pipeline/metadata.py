"""Step 7: metadata analysis & extraction — native PDF metadata + what the pipeline found."""

from __future__ import annotations

from collections import Counter


def build_metadata(pdf_metadata: dict, all_regions: list[dict], artifacts: list[dict], malformed_tables: list[str]) -> dict:
    class_counts = Counter(r["class"] for r in all_regions if not r.get("dropped"))
    low_confidence = [
        {"page": r["page"], "class": r["class"], "score": r["score"], "bbox": r["bbox"]}
        for r in all_regions
        if r.get("low_confidence") and not r.get("dropped")
    ]
    # Regions the layout model classified as "abandon" (headers/footers/watermarks) are
    # excluded from the markdown body, but still logged here -- without this, a region the
    # detector mislabels as abandon (e.g. a logo) would vanish with no trace anywhere.
    dropped_regions = [
        {"page": r["page"], "class": r["class"], "score": r["score"], "bbox": r["bbox"]}
        for r in all_regions
        if r.get("dropped")
    ]

    return {
        "pdf_metadata": pdf_metadata,
        "region_class_counts": dict(class_counts),
        "artifacts_detected": artifacts,
        "low_confidence_regions": low_confidence,
        "dropped_regions": dropped_regions,
        "malformed_table_count": len(malformed_tables),
    }


def build_regions_export(all_regions: list[dict]) -> list[dict]:
    """The full per-region layout record for every region that actually made it
    into the markdown body -- true DocLayout-YOLO class, confidence score, page,
    bbox, and clean (undecorated) text. This is the actual layout understanding
    Module 1 produced; downstream consumers (Module 3's chunker) should read
    this instead of re-guessing structure by regex-parsing the rendered
    markdown, which loses class granularity (captions/formulas collapse into
    indistinguishable plain text) and confidence scores entirely.
    """
    return [
        {
            "page": r["page"],
            "class": r["class"],
            "score": r["score"],
            "bbox": r["bbox"],
            "text": r["text"],
            "low_confidence": r["low_confidence"],
            **({"extra": r["extra"]} if r.get("extra") else {}),
        }
        for r in all_regions
        if r.get("markdown")
    ]
