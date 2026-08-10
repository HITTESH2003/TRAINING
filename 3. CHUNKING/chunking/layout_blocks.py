"""Builds typed content blocks directly from Module 1's regions.json -- the
actual DocLayout-YOLO + VLM classification for every region, not a re-guess
from the rendered markdown's formatting syntax.

This replaces the earlier approach (still in blocks.py, kept only for
fixed_size/recursive which deliberately want raw undifferentiated text) of
regex-parsing `#`/`<table`/`![...]` back out of the markdown file. That
approach worked but silently lost information Module 1 already had:

  - table_caption, table_footnote, and formula_caption all collapse into
    indistinguishable "paragraph" blocks once rendered to markdown as plain
    or italic text -- regex can't tell them apart from a genuine body
    paragraph, but the layout detector already told us exactly what they
    are, and that's preserved here in extra["layout_class"].
  - per-region confidence scores don't exist in markdown at all. Reading
    them from regions.json means a chunk built partly from a shaky OCR
    region can actually say so (see extra["low_confidence"] and how
    hierarchical.py surfaces it as a chunk-level note).

The block TYPE used for chunking decisions (heading/paragraph/table/figure)
is still the same four-way split -- tables and figures need to stay atomic
either way -- but it's now derived from the real class label, and the real
label is preserved alongside it.
"""

from __future__ import annotations

import json
from pathlib import Path

from .blocks import Block

_TITLE_CLASSES = {"title"}
_TABLE_CLASSES = {"table"}
_FIGURE_CLASSES = {"figure"}
# everything else (plain text, table_caption, table_footnote, isolate_formula,
# formula_caption, or any class the pipeline didn't specifically route) is a
# paragraph-type block for chunking purposes -- small, splittable, not atomic.


def regions_path_for(ocr_doc_dir: Path) -> Path:
    return ocr_doc_dir / "regions.json"


def load_layout_blocks(regions_json_path: Path) -> list[Block]:
    records = json.loads(regions_json_path.read_text(encoding="utf-8"))
    blocks: list[Block] = []

    for record in records:
        layout_class = record["class"]
        extra = {
            "layout_class": layout_class,
            "confidence": record["score"],
            "low_confidence": record.get("low_confidence", False),
        }
        if record.get("extra"):
            extra.update(record["extra"])

        if layout_class in _TITLE_CLASSES:
            blocks.append(Block("heading", record["text"], record["page"], level=2, extra=extra))
        elif layout_class in _TABLE_CLASSES:
            blocks.append(Block("table", record["text"], record["page"], extra=extra))
        elif layout_class in _FIGURE_CLASSES:
            blocks.append(Block("figure", record["text"], record["page"], extra=extra))
        else:
            blocks.append(Block("paragraph", record["text"], record["page"], extra=extra))

    return blocks
