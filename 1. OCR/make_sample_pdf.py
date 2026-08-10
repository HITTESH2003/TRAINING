"""Generates a small synthetic PDF that deliberately exercises every region
class the pipeline routes on: title, plain text, table + table_caption,
figure (chart / logo / signature / stamp_seal) + figure_caption,
isolate_formula + formula_caption, and a footer (abandon).

Unlike the real-world government PDFs, this one has known ground truth --
useful for checking the pipeline's output against what it *should* produce,
and later as a structurally simple, single-page fixture for testing chunking
strategies (heading-based, fixed-size, recursive, ...) since its section
boundaries are known in advance rather than inferred.

All names/branding here are fictional placeholders (no real company, agency,
or person), invented purely for this test fixture.
"""

from __future__ import annotations

import io
import random

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pymupdf
from PIL import Image, ImageDraw

OUT_PATH = "input_pdfs/synthetic_sample.pdf"


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_logo() -> bytes:
    img = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((10, 10, 190, 190), fill=(30, 90, 200, 255))
    draw.text((58, 82), "AA", fill="white")
    return _png_bytes(img)


def make_signature() -> bytes:
    img = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    random.seed(7)
    points = [(10 + i * 12, 50 + random.randint(-25, 25)) for i in range(24)]
    draw.line(points, fill=(20, 20, 120, 255), width=3, joint="curve")
    return _png_bytes(img)


def make_stamp() -> bytes:
    img = Image.new("RGBA", (180, 180), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((5, 5, 175, 175), outline=(200, 30, 30, 255), width=6)
    draw.ellipse((20, 20, 160, 160), outline=(200, 30, 30, 255), width=2)
    draw.text((52, 82), "APPROVED", fill=(200, 30, 30, 255))
    return _png_bytes(img)


def make_chart() -> bytes:
    fig, ax = plt.subplots(figsize=(4, 2.5), dpi=150)
    categories = ["Region A", "Region B", "Region C", "Region D"]
    values = [42, 68, 51, 77]
    ax.bar(categories, values, color="#2f6fb0")
    ax.set_title("Q3 Regional Output")
    ax.set_ylabel("Units (thousands)")
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def inset(rect: pymupdf.Rect, pad: float) -> pymupdf.Rect:
    return pymupdf.Rect(rect.x0 + pad, rect.y0 + pad, rect.x1 - pad, rect.y1 - pad)


def build() -> None:
    doc = pymupdf.open()
    doc.set_metadata(
        {
            "title": "Synthetic Training Fixture",
            "author": "OCR pipeline test generator",
            "subject": "Layout-detection test document (fictional content)",
        }
    )
    page = doc.new_page(width=612, height=792)  # US Letter

    # logo (artifact)
    page.insert_image(pymupdf.Rect(470, 40, 550, 120), stream=make_logo())

    # title
    page.insert_textbox(
        pymupdf.Rect(60, 55, 460, 100),
        "Q3 Regional Operations Report",
        fontsize=20,
        fontname="helv",
    )

    # plain text, two separate paragraphs
    para1 = (
        "This report summarizes regional operational output for the third "
        "quarter. Overall throughput increased across three of the four "
        "monitored regions, driven primarily by expanded shift coverage and "
        "reduced equipment downtime."
    )
    page.insert_textbox(pymupdf.Rect(60, 140, 552, 205), para1, fontsize=11, fontname="helv")

    para2 = (
        "Region B continues to lead in total output, while Region A shows "
        "the largest quarter-over-quarter improvement. Details for each "
        "region are provided in the table below."
    )
    page.insert_textbox(pymupdf.Rect(60, 220, 552, 275), para2, fontsize=11, fontname="helv")

    # table caption
    # NOTE: PyMuPDF's insert_textbox silently renders NOTHING if the box is even a
    # few points too short for one line -- no error, no partial line. Every box
    # below gives >=20pt of height per text line (empirically the minimum for
    # 9-11pt Helvetica to reliably fit; verified against actual return values).
    page.insert_textbox(
        pymupdf.Rect(60, 288, 552, 308),
        "Table 1. Output by region, in thousands of units.",
        fontsize=9,
        fontname="helv",
    )

    # table (drawn grid + text)
    table_rows = [
        ["Region", "Q2", "Q3", "Change"],
        ["Region A", "31", "42", "+35%"],
        ["Region B", "60", "68", "+13%"],
        ["Region C", "55", "51", "-7%"],
        ["Region D", "70", "77", "+10%"],
    ]
    tx0, ty0 = 60, 312
    col_w = [130, 100, 100, 100]
    row_h = 26
    for r, row in enumerate(table_rows):
        x = tx0
        for c, cell in enumerate(row):
            rect = pymupdf.Rect(x, ty0 + r * row_h, x + col_w[c], ty0 + (r + 1) * row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.75)
            page.insert_textbox(inset(rect, 3), cell, fontsize=9, fontname="helv")
            x += col_w[c]
    table_bottom = ty0 + len(table_rows) * row_h

    # chart + caption
    chart_rect = pymupdf.Rect(60, table_bottom + 20, 340, table_bottom + 200)
    page.insert_image(chart_rect, stream=make_chart())
    page.insert_textbox(
        pymupdf.Rect(60, table_bottom + 202, 340, table_bottom + 222),
        "Figure 1. Regional output, Q3.",
        fontsize=9,
        fontname="helv",
    )

    # formula + caption (widened so the formula fits on one line at 9pt)
    page.insert_textbox(
        pymupdf.Rect(335, table_bottom + 20, 552, table_bottom + 40),
        "Efficiency = Output / (Hours x Headcount)",
        fontsize=9,
        fontname="helv",
    )
    page.insert_textbox(
        pymupdf.Rect(335, table_bottom + 42, 552, table_bottom + 62),
        "Eq. 1. Efficiency ratio used for regional comparison.",
        fontsize=9,
        fontname="helv",
    )

    # signature + stamp near bottom
    sig_y = table_bottom + 230
    page.insert_image(pymupdf.Rect(60, sig_y, 260, sig_y + 60), stream=make_signature())
    page.insert_textbox(
        pymupdf.Rect(60, sig_y + 62, 260, sig_y + 76),
        "J. Alvarez, Regional Director",
        fontsize=8,
        fontname="helv",
    )
    page.insert_image(pymupdf.Rect(420, sig_y - 20, 520, sig_y + 80), stream=make_stamp())

    # footer (abandon)
    page.insert_textbox(
        pymupdf.Rect(60, 760, 552, 775),
        "Internal use only  |  Page 1 of 1  |  Doc ID: SAMPLE-2026-Q3-001",
        fontsize=8,
        fontname="helv",
    )

    doc.save(OUT_PATH)
    doc.close()
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    build()
