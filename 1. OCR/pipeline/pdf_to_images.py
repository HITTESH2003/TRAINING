"""Step 1: PDF -> page images."""

from __future__ import annotations

from pathlib import Path

import pymupdf as fitz


def render_pdf_pages(pdf_path: Path, pages_dir: Path, dpi: int) -> list[Path]:
    """Render every page of pdf_path to a PNG in pages_dir. Returns page image paths in order."""
    pages_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    page_paths = []
    doc = fitz.open(pdf_path)
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat)
            page_path = pages_dir / f"page_{i + 1:03d}.png"
            pix.save(str(page_path))
            page_paths.append(page_path)
    finally:
        doc.close()

    return page_paths


def read_pdf_metadata(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    try:
        return {
            "page_count": doc.page_count,
            **{k: v for k, v in doc.metadata.items() if v},
        }
    finally:
        doc.close()
