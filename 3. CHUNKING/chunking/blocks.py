"""The shared content-block record type used across the chunking strategies.

Blocks are built by layout_blocks.py, straight from Module 1's regions.json
(the real DocLayout-YOLO + VLM classification for every region) -- not by
re-parsing the rendered markdown's formatting syntax. An earlier version of
this module did the latter (regex for `#`, `<table`, `![...]`) before
Module 1 persisted regions.json; it worked, but silently collapsed
table_caption/table_footnote/formula_caption into indistinguishable
"paragraph" blocks and had no access to per-region confidence scores at all.
Once real layout data was available there was no reason to keep guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

BlockType = str  # "heading" | "paragraph" | "table" | "figure"


@dataclass
class Block:
    type: BlockType
    text: str
    page: Optional[int] = None
    level: Optional[int] = None  # heading level only (2 = section; see layout_blocks.py)
    extra: dict = field(default_factory=dict)
