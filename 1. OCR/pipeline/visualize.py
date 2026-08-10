"""Draws detected region boxes + class labels on a page image.

For a teaching session, this matters more than the raw region list: students
can see exactly what the layout detector found (and got wrong) directly on
the page, rather than reading a table of coordinates.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# One color per DocLayout-YOLO class, reused across a document so the same
# class always reads the same color on every page.
_COLORS: dict[str, tuple[int, int, int]] = {
    "title": (214, 39, 40),
    "plain text": (31, 119, 180),
    "table": (44, 160, 44),
    "table_caption": (44, 160, 44),
    "table_footnote": (44, 160, 44),
    "figure": (255, 127, 14),
    "figure_caption": (255, 127, 14),
    "isolate_formula": (148, 103, 189),
    "formula_caption": (148, 103, 189),
    "abandon": (127, 127, 127),
}
_DEFAULT_COLOR = (0, 0, 0)
_BOX_WIDTH = 4


def _color_for(cls: str) -> tuple[int, int, int]:
    return _COLORS.get(cls, _DEFAULT_COLOR)


def _load_font(size: int) -> ImageFont.ImageFont:
    for name in ("Arial.ttf", "DejaVuSans-Bold.ttf", "Helvetica.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_regions(page_image: Image.Image, regions: list[dict]) -> Image.Image:
    """Returns a copy of page_image with every region's box + 'class score' label drawn on it."""
    annotated = page_image.convert("RGB").copy()
    draw = ImageDraw.Draw(annotated)
    font = _load_font(24)

    for region in regions:
        x0, y0, x1, y1 = region["bbox"]
        color = _color_for(region["class"])
        draw.rectangle([x0, y0, x1, y1], outline=color, width=_BOX_WIDTH)

        label = f"{region['class']} {region['score']:.2f}"
        text_box = draw.textbbox((0, 0), label, font=font)
        text_w, text_h = text_box[2] - text_box[0], text_box[3] - text_box[1]
        label_top = max(0, y0 - text_h - 8)
        draw.rectangle([x0, label_top, x0 + text_w + 8, label_top + text_h + 8], fill=color)
        draw.text((x0 + 4, label_top + 4), label, fill=(255, 255, 255), font=font)

    return annotated


def save_annotated(page_image: Image.Image, regions: list[dict], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    draw_regions(page_image, regions).save(out_path)
