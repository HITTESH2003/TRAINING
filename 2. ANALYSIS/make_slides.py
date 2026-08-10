"""Builds Analysis_Module_Overview.pptx -- a teaching deck for Module 2 (Analysis).

Every number in this deck comes from actually running analyze.py against
Module 1's real output (3 documents, as of this writing) -- not illustrative
placeholders. Re-run analyze.py first if you want the deck to reflect a
fresh Module 1 run; this script doesn't re-run it for you.

Same visual design system as 1. OCR/make_slides.py, duplicated here rather
than imported -- each module stays self-contained and only shares the venv,
same convention as tokenizer_util.py existing separately in both modules.

Usage:
  python make_slides.py
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent
OUT_PATH = ROOT / "Analysis_Module_Overview.pptx"

# ---- palette (matches 1. OCR/make_slides.py) --------------------------------
DARK = RGBColor(0x0F, 0x17, 0x2A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1A, 0x1D, 0x27)
MUTED = RGBColor(0x8A, 0x93, 0xA6)
MUTED_DARK = RGBColor(0x5B, 0x63, 0x74)
ACCENT = RGBColor(0x3E, 0x8E, 0xDE)       # blue -- structural/technical content
ACCENT_WARM = RGBColor(0xF2, 0xA6, 0x3D)  # amber -- "did you know" slides
ACCENT_GOOD = RGBColor(0x4C, 0xAF, 0x7D)  # green -- real code slides
ACCENT_BAD = RGBColor(0xE0, 0x6C, 0x5C)   # red -- real findings / case studies
CODE_BG = RGBColor(0x1E, 0x1E, 0x2E)
CODE_TEXT = RGBColor(0xA6, 0xE3, 0xA1)

FONT_BODY = "Calibri"
FONT_CODE = "Consolas"

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)


def _set_bg(slide, color: RGBColor) -> None:
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def _blank(prs: Presentation):
    return prs.slides.add_slide(prs.slide_layouts[6])


def _textbox(slide, left, top, width, height, text, size, color, bold=False, italic=False, align=PP_ALIGN.LEFT, font=FONT_BODY):
    box = slide.shapes.add_textbox(left, top, width, height)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.color.rgb = color
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font
    return box


def _kicker(slide, text, color=ACCENT):
    _textbox(slide, Inches(0.7), Inches(0.45), Inches(11.9), Inches(0.5), text.upper(), 15, color, bold=True)


def _accent_bar(slide, color, top=Inches(0), height=Inches(0.12)):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), top, SLIDE_W, height)
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    return bar


def _page_number(slide, n, dark=False):
    color = MUTED if dark else MUTED_DARK
    _textbox(slide, Inches(12.6), Inches(7.05), Inches(0.6), Inches(0.35), str(n), 11, color, align=PP_ALIGN.RIGHT)


# ---- adaptive bullet sizing (fits content instead of guessing a fixed size) --

_BULLET_SIZE_PRESETS = [
    (20, 16, 12, 6),
    (18, 15, 10, 5),
    (16, 13, 8, 4),
    (14.5, 12, 6, 3),
]


def _estimate_block_height_in(bullets, box_w_in, size0, size1, space0, space1, prefix0_len=3, prefix1_len=8):
    total = 0.0
    for level, text in bullets:
        size = size0 if level == 0 else size1
        space = space0 if level == 0 else space1
        prefix_len = prefix0_len if level == 0 else prefix1_len
        chars_per_line = max(10, int(box_w_in / (0.5 * size / 72)))
        lines = max(1, -(-(len(text) + prefix_len) // chars_per_line))
        line_height_in = (size * 1.22) / 72
        total += lines * line_height_in + space / 72
    return total


def _pick_bullet_sizes(bullets, box_w_in, box_h_in, presets=_BULLET_SIZE_PRESETS, safety_margin=0.88):
    # Require the estimate to clear a margin, not just technically fit --
    # the char-count-based line-wrap estimate is approximate, so an exact
    # fit on paper can still overflow once real font metrics render it.
    budget = box_h_in * safety_margin
    for preset in presets:
        if _estimate_block_height_in(bullets, box_w_in, *preset) <= budget:
            return preset
    return presets[-1]


def _fill_bullets(tf, bullets, size0, size1, space0, space1):
    first = True
    for level, text in bullets:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(space0 if level == 0 else space1)
        prefix = "▸  " if level == 0 else "     –  "
        run = p.add_run()
        run.text = prefix + text
        run.font.size = Pt(size0 if level == 0 else size1)
        run.font.color.rgb = INK if level == 0 else MUTED_DARK
        run.font.name = FONT_BODY
        run.font.bold = level == 0


# ---- slide builders ---------------------------------------------------------

def add_title_slide(prs, kicker, title, subtitle, footer):
    slide = _blank(prs)
    _set_bg(slide, DARK)
    _accent_bar(slide, ACCENT)
    _textbox(slide, Inches(1), Inches(2.5), Inches(11.3), Inches(0.5), kicker.upper(), 18, ACCENT, bold=True)
    _textbox(slide, Inches(1), Inches(3.0), Inches(11.3), Inches(1.6), title, 44, WHITE, bold=True)
    _textbox(slide, Inches(1), Inches(4.35), Inches(11.3), Inches(1.0), subtitle, 20, MUTED)
    _textbox(slide, Inches(1), Inches(6.7), Inches(11.3), Inches(0.5), footer, 13, MUTED_DARK)
    return slide


def add_bullet_slide(prs, kicker, title, bullets, page, color=ACCENT, note=None):
    slide = _blank(prs)
    _set_bg(slide, WHITE)
    _accent_bar(slide, color)
    _kicker(slide, kicker, color=color)
    _textbox(slide, Inches(0.7), Inches(0.85), Inches(11.9), Inches(0.9), title, 30, INK, bold=True)

    box_w_in, box_h_in = 11.7, 4.9
    sizes = _pick_bullet_sizes(bullets, box_w_in, box_h_in)
    box = slide.shapes.add_textbox(Inches(0.8), Inches(1.85), Inches(box_w_in), Inches(box_h_in))
    tf = box.text_frame
    tf.word_wrap = True
    _fill_bullets(tf, bullets, *sizes)

    if note:
        _textbox(slide, Inches(0.8), Inches(6.85), Inches(11.7), Inches(0.45), note, 12, MUTED_DARK, italic=True)

    _page_number(slide, page)
    return slide


def add_fact_slide(prs, kicker, title, bullets, page, color=ACCENT_WARM):
    slide = add_bullet_slide(prs, kicker, title, bullets, page, color=color)
    tag = slide.shapes.add_textbox(Inches(10.6), Inches(0.42), Inches(2.0), Inches(0.5))
    tf = tag.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.RIGHT
    run = p.add_run()
    run.text = "★ DID YOU KNOW"
    run.font.size = Pt(12)
    run.font.bold = True
    run.font.color.rgb = ACCENT_WARM
    return slide


def add_code_slide(prs, kicker, title, label, code_text, note, page):
    slide = _blank(prs)
    _set_bg(slide, WHITE)
    _accent_bar(slide, ACCENT_GOOD)
    _kicker(slide, kicker, color=ACCENT_GOOD)
    _textbox(slide, Inches(0.7), Inches(0.85), Inches(11.9), Inches(0.7), title, 28, INK, bold=True)
    _textbox(slide, Inches(0.8), Inches(1.55), Inches(11), Inches(0.4), label, 14, MUTED_DARK, bold=True)

    card = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(2.0), Inches(11.7), Inches(4.0))
    card.fill.solid()
    card.fill.fore_color.rgb = CODE_BG
    card.line.fill.background()
    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.35)
    tf.margin_right = Inches(0.35)
    tf.margin_top = Inches(0.3)
    tf.margin_bottom = Inches(0.3)
    tf.vertical_anchor = MSO_ANCHOR.TOP
    first = True
    for line in code_text.split("\n"):
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        run = p.add_run()
        run.text = line if line.strip() else " "
        run.font.size = Pt(14)
        run.font.name = FONT_CODE
        run.font.color.rgb = CODE_TEXT

    _textbox(slide, Inches(0.8), Inches(6.2), Inches(11.7), Inches(1.0), note, 14, MUTED_DARK, italic=True)
    _page_number(slide, page)
    return slide


def add_table_slide(prs, kicker, title, headers, rows, page, color=ACCENT, note=None):
    """A real small data table -- for showing actual numbers, not bullets pretending to be numbers."""
    slide = _blank(prs)
    _set_bg(slide, WHITE)
    _accent_bar(slide, color)
    _kicker(slide, kicker, color=color)
    _textbox(slide, Inches(0.7), Inches(0.85), Inches(11.9), Inches(0.7), title, 28, INK, bold=True)

    n_rows, n_cols = len(rows) + 1, len(headers)
    left, top, width, height = Inches(0.8), Inches(2.0), Inches(11.7), Inches(0.55 * n_rows)
    gshape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    table = gshape.table

    for c, header in enumerate(headers):
        cell = table.cell(0, c)
        cell.text = header
        cell.fill.solid()
        cell.fill.fore_color.rgb = color
        for p in cell.text_frame.paragraphs:
            p.alignment = PP_ALIGN.LEFT
            for run in p.runs:
                run.font.bold = True
                run.font.size = Pt(14)
                run.font.color.rgb = WHITE
                run.font.name = FONT_BODY

    for r, row in enumerate(rows, start=1):
        for c, value in enumerate(row):
            cell = table.cell(r, c)
            cell.text = str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else RGBColor(0xF2, 0xF4, 0xF8)
            for p in cell.text_frame.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(14)
                    run.font.color.rgb = INK
                    run.font.name = FONT_BODY

    if note:
        note_top = top + height + Inches(0.3)
        _textbox(slide, Inches(0.8), note_top, Inches(11.7), Inches(1.2), note, 14, MUTED_DARK, italic=True)

    _page_number(slide, page)
    return slide


def add_closing_slide(prs, title, subtitle, footer):
    slide = _blank(prs)
    _set_bg(slide, DARK)
    _accent_bar(slide, ACCENT)
    _textbox(slide, Inches(1), Inches(3.0), Inches(11.3), Inches(1.2), title, 40, WHITE, bold=True)
    _textbox(slide, Inches(1), Inches(4.1), Inches(11.3), Inches(1.4), subtitle, 18, MUTED)
    _textbox(slide, Inches(1), Inches(6.7), Inches(11.3), Inches(0.5), footer, 13, MUTED_DARK)
    return slide


SERIES_MODULES = [
    (1, "OCR & Document Understanding", "PDF to structured markdown"),
    (2, "Analysis & Validation", "Is the extraction actually right?"),
    (3, "Chunking", "Splitting documents for retrieval"),
    (4, "Embedding & Database", "Vectors, Postgres, pgvector"),
    (5, "Database Deep Dive", "Search, indexes, and what Postgres actually does"),
    (6, "Summarization", "Retrieval + a real LLM + a UI"),
]


def add_series_intro_slide(prs, current_module, page):
    slide = _blank(prs)
    _set_bg(slide, WHITE)
    _accent_bar(slide, ACCENT)
    _kicker(slide, "Video Series")
    _textbox(slide, Inches(0.7), Inches(0.85), Inches(11.9), Inches(1.1), "Part of a Series: How to Build Your First Chatbot", 28, INK, bold=True)

    intro_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(0.9))
    tf = intro_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    run = p.add_run()
    run.text = (
        "This module is one step in a planned video series that builds a real, working "
        "chatbot end to end -- real documents, real models, real measured results, not toy examples."
    )
    run.font.size = Pt(16)
    run.font.color.rgb = MUTED_DARK
    run.font.name = FONT_BODY
    run.font.italic = True

    list_box = slide.shapes.add_textbox(Inches(0.8), Inches(3.05), Inches(11.7), Inches(3.0))
    tf2 = list_box.text_frame
    tf2.word_wrap = True
    first = True
    for num, name, desc in SERIES_MODULES:
        p = tf2.paragraphs[0] if first else tf2.add_paragraph()
        first = False
        p.space_after = Pt(10)
        is_current = num == current_module
        run = p.add_run()
        prefix = "►  " if is_current else "    "
        suffix = "   ◂ you are here" if is_current else ""
        run.text = f"{prefix}Module {num}: {name} -- {desc}{suffix}"
        run.font.size = Pt(18) if is_current else Pt(16)
        run.font.bold = is_current
        run.font.color.rgb = ACCENT if is_current else MUTED_DARK
        run.font.name = FONT_BODY

    _textbox(
        slide, Inches(0.8), Inches(6.3), Inches(11.7), Inches(0.8),
        "More modules are planned as the series continues toward a complete chatbot -- retrieval and response generation are next.",
        13, MUTED_DARK, italic=True,
    )

    _page_number(slide, page)
    return slide


# ---- deck content -----------------------------------------------------------

def build() -> None:
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    page = [0]

    def next_page():
        page[0] += 1
        return page[0]

    # 1 -- title
    add_title_slide(
        prs,
        kicker="Module 2 · Analysis",
        title="Validating What OCR Actually Extracted",
        subtitle="Module 1 produces a markdown file and says it's done. This module asks: is it actually right?",
        footer="analyze.py  ·  Qwen/Qwen3.5-0.8B tokenizer  ·  openpyxl",
    )
    next_page()

    # 2 -- series intro
    add_series_intro_slide(prs, current_module=2, page=next_page())

    # 3 -- why analysis
    add_bullet_slide(
        prs, "Why This Exists", "“Done” Is Not the Same as “Correct”",
        [
            (0, "Module 1 finishes every run the same way: a .md file and a metadata.json get written, no error, no warning"),
            (0, "That tells you the pipeline didn't crash. It tells you nothing about whether the output is trustworthy"),
            (0, "Module 2's job: turn the raw output of many documents into numbers you can actually look at and question"),
            (1, "page counts, token density, artifacts found, regions the model wasn't sure about, regions it dropped"),
            (0, "The deliverable is one Excel workbook -- because the person who needs to sanity-check 50 documents is rarely the person who wrote the pipeline"),
        ],
        next_page(),
    )

    # 3 -- fun fact: tokenization history
    add_fact_slide(
        prs, "Did you know", "“Tokens” Are Newer Than You'd Think",
        [
            (0, "Byte-Pair Encoding (BPE) -- the technique behind most modern LLM tokenizers -- was originally a 1994 data-COMPRESSION algorithm, not an AI technique at all"),
            (0, "It was repurposed for language models in 2015-2016, first for machine translation, years before GPT existed"),
            (0, "There is no universal “token” -- every model family (GPT, Qwen, Llama, Claude...) trains its own tokenizer on its own text, so the same sentence can produce a different token count in each one"),
            (1, "This is exactly why this module loads Qwen3.5-0.8B's own tokenizer instead of guessing -- see the next few slides"),
        ],
        next_page(),
    )

    # 4 -- what module 2 does
    add_bullet_slide(
        prs, "Overview", "What analyze.py Actually Does",
        [
            (0, "Reads every completed run in Module 1's output/ folder -- the .md file plus metadata.json"),
            (0, "Computes, per document: page count, word count, real token count, tokens/page, images and tables found in the body, artifact counts, low-confidence region count, dropped region count"),
            (0, "Writes one Excel workbook: a Summary sheet (one row per document) plus three detail sheets for anything worth a second look"),
            (0, "That's the whole module -- three files: stats.py (compute), tokenizer_util.py (count), report.py (write the workbook)"),
        ],
        next_page(),
    )

    # 5 -- setup: reuse venv
    add_bullet_slide(
        prs, "Engineering Detail", "No New 3GB Install",
        [
            (0, "Counting tokens the right way means loading a real tokenizer -- which means the transformers library, which Module 1 already installed"),
            (0, "Module 2 reuses Module 1's virtual environment directly instead of building its own"),
            (1, "requirements.txt for this whole module is one line: openpyxl"),
            (0, "Run it as:  \"../1. OCR/.venv/bin/python\" analyze.py"),
            (0, "A small thing, but a real one -- don't make a student re-download a gigabyte of ML libraries just to count tokens and write a spreadsheet"),
        ],
        next_page(),
    )

    # 6 -- the core question
    add_bullet_slide(
        prs, "The Core Question", "How Many Tokens Per Page, Really?",
        [
            (0, "“Word count” is not “token count.” A word can be one token, several tokens, or a fraction of a shared token -- it depends on the tokenizer"),
            (0, "Why this matters here specifically: every downstream step (Module 3's chunking, any embedding or LLM call) is budgeted in tokens, not words or characters"),
            (0, "So “how to check tokens per page” has one honest answer: load the SAME tokenizer the extraction model uses, and count what it actually produces"),
            (1, "Not estimate it. Not divide characters by 4. Count it."),
        ],
        next_page(),
    )

    # 7 -- real code: tokenizer_util.py
    add_code_slide(
        prs, "The Actual Code", "How Tokens/Page Is Actually Computed",
        "analysis/tokenizer_util.py",
        "from transformers import AutoTokenizer\n\n"
        "_TOKENIZER = AutoTokenizer.from_pretrained(config.TOKENIZER_MODEL_ID)\n\n"
        "def count_tokens(text: str) -> int:\n"
        "    return len(_TOKENIZER(text, add_special_tokens=False)[\"input_ids\"])\n\n"
        "# tokens_per_page = count_tokens(markdown_text) / page_count",
        "config.TOKENIZER_MODEL_ID is \"Qwen/Qwen3.5-0.8B\" -- the exact model Module 1 used to extract the text in the first place.",
        next_page(),
    )

    # 8 -- fun fact: token vs word
    add_fact_slide(
        prs, "Did you know", "A “Word” Can Be Several Tokens — or Less Than One",
        [
            (0, "Common English words are usually 1 token. Rare words, names, and numbers routinely split into 2-4 tokens"),
            (0, "Punctuation-dense, symbol-heavy text (legal citations, document IDs, markdown headers) tokenizes LESS efficiently than plain prose -- more tokens for the same character count"),
            (0, "That's not a guess -- it's exactly what shows up two slides from now, comparing real documents from this project"),
        ],
        next_page(),
    )

    # 9 -- real numbers table
    add_table_slide(
        prs, "Real Numbers", "Tokens Per Page, Three Real Documents",
        ["Document", "Pages", "Tokens", "Tokens / Page"],
        [
            ["federal_register_proclamation", 3, 1526, "508.7"],
            ["synthetic_sample", 1, 513, "513.0"],
            ["nasa_iss_factsheet", 2, 495, "247.5"],
        ],
        next_page(),
        note="The dense legal proclamation and the structured synthetic page (table + chart + formula) land almost identically dense -- ~510 tokens/page. The NASA fact sheet's plain prose runs at roughly half that. Content density drives this number more than document length does.",
    )

    # 10 -- what else gets measured
    add_bullet_slide(
        prs, "What Else Gets Measured", "Beyond Just Tokens",
        [
            (0, "images_in_body / tables_in_body -- counted directly from the markdown (![...] and <table occurrences)"),
            (0, "logo_count / signature_count / stamp_seal_count / other_artifact_count -- tallied from metadata.json's artifacts_detected"),
            (0, "low_confidence_count -- regions the layout detector itself flagged as uncertain"),
            (0, "dropped_region_count -- regions excluded from the document body (headers/footers, or misclassified content -- see Module 1's README)"),
            (0, "malformed_table_count -- any <table> that failed a basic HTML tag-balance check"),
            (0, "Plus native PDF metadata: title, author, creation date -- blank when the source PDF never set them"),
        ],
        next_page(),
    )

    # 11 -- excel report structure
    add_bullet_slide(
        prs, "The Deliverable", "One Workbook, Four Sheets",
        [
            (0, "Summary -- one row per document, every stat from the last two slides in one place"),
            (0, "Artifacts Detail -- one row per detected logo/signature/stamp_seal: page, description, bounding box"),
            (0, "Low Confidence Regions -- one row per region the layout detector wasn't sure about"),
            (0, "Dropped Regions -- one row per region excluded from the body, including anything misclassified as page furniture"),
            (1, "Cross-reference any bbox here against Module 1's output/<doc>/annotated/ images to see exactly what was found"),
        ],
        next_page(),
    )

    # 12 -- fun fact: spreadsheet history
    add_fact_slide(
        prs, "Did you know", "The Spreadsheet Predates the Personal Computer Boom",
        [
            (0, "VisiCalc (1979) is widely credited as the first electronic spreadsheet -- and the first “killer app” that sold people on owning a computer at all"),
            (0, "Excel itself shipped in 1985, for the original Apple Macintosh, two years before it ever ran on Windows"),
            (0, "Forty-plus years later, it's still the default format for “give me a report I can actually open and check” -- which is exactly why this module writes .xlsx and not just another .json file"),
        ],
        next_page(),
    )

    # 13 -- real case study: dropped regions traceability
    add_bullet_slide(
        prs, "Real Case Study", "Tracing a Dropped Region Back to a Real Bug",
        [
            (0, "synthetic_sample's Dropped Regions sheet has a row: class “abandon”, confidence 0.46, bbox [1312, 117, 1521, 329]"),
            (0, "That bbox is the document's logo -- a real image region the layout detector misclassified as page furniture and dropped before it ever reached the VLM's figure classifier"),
            (0, "It's visible directly in Module 1's output/synthetic_sample/annotated/page_001.png: a gray “abandon” box drawn right over the logo"),
            (1, "This is the whole point of keeping Dropped Regions instead of silently discarding them -- a bounding box and a confidence score turn a hidden bug into a traceable, screenshot-able one"),
        ],
        next_page(),
        color=ACCENT_BAD,
    )

    # 14 -- validation as anomaly detection habit
    add_bullet_slide(
        prs, "A Validation Habit", "Tokens/Page as an Anomaly Signal",
        [
            (0, "There's no universal “correct” tokens-per-page number -- it depends entirely on the document type"),
            (0, "But once you have it for a batch of similar documents, an outlier is worth a look:"),
            (1, "Much LOWER than its peers -- possible sign of missed or truncated content"),
            (1, "Much HIGHER than its peers -- possible sign of garbled or repeated OCR output (Module 1's own README documents a duplicate-detection bug that does exactly this)"),
            (0, "The value of this sheet isn't any single number -- it's being able to scan 50 rows and immediately see which ones don't look like the rest"),
        ],
        next_page(),
    )

    # 15 -- what counts as a document
    add_bullet_slide(
        prs, "A Quiet Detail", "Partial Runs Get Skipped, Not Guessed At",
        [
            (0, "A folder in Module 1's output/ only counts as “a document” if it has BOTH <name>.md AND metadata.json"),
            (0, "An interrupted or still-running Module 1 job leaves a folder with pages/ and maybe some images/, but no .md and no metadata.json yet"),
            (0, "analyze.py silently skips those rather than guessing at partial data -- a document either finished, or it isn't analyzed at all"),
        ],
        next_page(),
    )

    # 16 -- wrap-up
    add_bullet_slide(
        prs, "Wrap-Up", "What Module 2 Actually Produces",
        [
            (0, "ocr_analysis_report.xlsx -- Summary + 3 detail sheets, one workbook covering every document Module 1 has processed"),
            (0, "Real, exact token counts -- from the same tokenizer the extraction model used, not an approximation"),
            (0, "A traceable audit trail -- every flagged region carries a bbox back to Module 1's annotated screenshots"),
            (0, "Next: Module 3 takes this same output and turns it into retrieval-ready chunks -- recursive, semantic, and hierarchical strategies, compared on the same real documents"),
        ],
        next_page(),
    )

    # 17 -- closing
    add_closing_slide(
        prs,
        title="Questions?",
        subtitle="2. ANALYSIS/  --  README.md has the full column-by-column report reference and every real number in this deck.",
        footer="Module 2 of 3  ·  Data Processing → Analysis → Chunking",
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT_PATH)
    print(f"wrote {OUT_PATH}  ({len(prs.slides)} slides)")


if __name__ == "__main__":
    build()
