# Module 1: Data Processing — PDF → Markdown pipeline

Teaching pipeline: given a PDF, walk every step from page image to
classified regions to a clean markdown file, using a small doc-layout
detector + a small vision-language model (Qwen3.5-0.8B).

## Folder layout

```
OCR/
  input_pdfs/         sample PDFs live here (2 included, see below) -- drop your own in too
  output/             results land here, one subfolder per PDF
  pipeline/           the 7 pipeline steps, one file each, plus device.py and
                      visualize.py (shared backend selection / bounding-box rendering)
  run_pipeline.py     CLI entrypoint
  make_sample_pdf.py  builds a synthetic single-page PDF covering every region class at
                      once, with known ground truth -- not run by default, useful if you
                      want a controlled fixture beyond the two real-world samples
```

## Setup

**Requires Python 3.10 or newer** -- `transformers` (needed for Qwen3.5) will not
install on anything older, and pip's error message when that happens does not
mention Python at all, it just claims no matching version exists. Check first:

```bash
python3 --version
```

If that's below 3.10, get a newer interpreter before doing anything else --
e.g. with pyenv: `pyenv install 3.11.9 && pyenv local 3.11.9` (run from inside
this `OCR/` folder; `pyenv local` writes a `.python-version` file that pins
just this project, nothing system-wide). Then:

```bash
cd OCR
python3 -m venv .venv && source .venv/bin/activate
python --version          # confirm the venv actually picked up 3.10+
pip install -r ../requirements.txt   # one shared file, covers all 6 modules
```

First run downloads two models automatically (cached by huggingface_hub):
- `juliozhao/DocLayout-YOLO-DocStructBench` (layout detector, ~40MB)
- `Qwen/Qwen3.5-0.8B` (vision-language model, ~1.6GB)

## Sample PDFs included

`input_pdfs/` has two to start with -- kept deliberately minimal for a
first OCR session. Both are single-column and 3 pages or fewer, so the
pipeline's naive top-to-bottom reading order (see "Known simplifications"
below) produces correct output:

| File | Pages | What it's for |
|---|---|---|
| `federal_register_proclamation.pdf` | 3 | Real govinfo.gov document. Letterhead/logo + a signature artifact. Start here. |
| `nasa_iss_factsheet.pdf` | 2 | Real NASA fact sheet. Logo, plain paragraphs, a bulleted list. |

**Deliberately not included**: real government PDFs are very often
multi-column (Census Bureau briefs, IRS instruction pages, many federal
register notices past the first page). Two such files were tested and
removed from this set specifically because the naive reading-order sort
scrambles them -- worth fetching one back as a class exercise in *why*
that happens and what a smarter sort would need (column detection before
top-to-bottom sort, not after).

## Run

```bash
python run_pipeline.py                    # everything in input_pdfs/
python run_pipeline.py --input one.pdf     # a single file
python run_pipeline.py --input some_dir/   # a specific folder of PDFs
python run_pipeline.py --output custom/    # write elsewhere
python run_pipeline.py --device cpu        # force a backend instead of auto-picking
```

### Device selection (`pipeline/device.py`)

Both the layout detector and the VLM pick a backend automatically: CUDA GPU >
Apple Silicon MPS > CPU. This is worth walking through with students — it's a
real-world concern with every local model, not specific to this pipeline:

- `--device` lets you force a specific backend to compare speed/behavior
  (e.g. run the same PDF with `--device cpu` vs the auto-picked `mps`).
- Requesting a device that isn't actually there (`--device cuda` on a machine
  with no NVIDIA GPU) fails immediately with a clear error, rather than
  quietly falling back or crashing deep inside a tensor op.
- If a specific operation isn't implemented on the chosen backend at
  *runtime* (this does happen on MPS for some kernels), the pipeline logs a
  warning and retries that call on CPU rather than dying mid-batch.

## What happens, step by step

1. **PDF → image** (`pipeline/pdf_to_images.py`) — each page rendered to a
   PNG at 200 DPI.
2. **Layout detection** (`pipeline/layout_detect.py`) — DocLayout-YOLO
   classifies regions on each page image: `title`, `plain text`, `table`,
   `figure`, `figure_caption`, `table_caption`, `table_footnote`,
   `isolate_formula`, `formula_caption`, `abandon` (headers/footers/
   watermarks). Immediately after, `pipeline/visualize.py` draws every box
   + its class/confidence label straight onto the page image and saves it
   to `annotated/` — this happens before any VLM call, so you can see
   exactly what the detector found (including its mistakes, like duplicate
   overlapping boxes) without waiting on model generation.
3. **Per-region extraction** (`pipeline/vlm_client.py` +
   `pipeline/region_router.py`) — each cropped region goes to
   Qwen3.5-0.8B:
   - `title` / `plain text` / captions / formulas → OCR transcription
   - `table` → asked directly for an HTML `<table>` element
   - `figure` → asked to classify itself as `chart`, `photo`, `diagram`,
     `logo`, `signature`, `stamp_seal`, or `other`, plus a one-sentence
     description
   - `abandon` → dropped from the markdown body, still logged
4. **Artifact handling** — `logo` / `signature` / `stamp_seal` figures are
   **not** inlined into the document body. They're recorded in
   `metadata.json` (page, type, description, bbox) since they're page
   furniture / provenance markers, not document content.
5. **Assembly** (`pipeline/assemble.py`) — regions concatenated in reading
   order (top-to-bottom, left-to-right per page — a single-column
   simplification; a real multi-column PDF will need a smarter sort, which
   is a good extension exercise).
6. **Post-processing** (`pipeline/postprocess.py`) — whitespace cleanup,
   and a basic HTML tag-balance check on every `<table>` block (malformed
   ones are flagged in the console output and left in place for manual
   review, not silently dropped).
7. **Metadata** (`pipeline/metadata.py`) — native PDF metadata (author,
   title, dates) + derived stats: region counts per class, artifacts
   found, and any low-confidence detections worth a second look.

## Output per PDF

```
output/<pdf-name>/
  pages/            rendered page PNGs
  annotated/        same pages with detected region boxes + class/score labels drawn on -- start here to sanity-check the layout step
  images/            cropped chart/photo/diagram figures used in the markdown
  <pdf-name>.md      final markdown: text + inline HTML tables + figure descriptions
  metadata.json      pdf metadata + region counts + artifacts + low-confidence flags + dropped regions
  regions.json       full per-region record for everything that reached the markdown body:
                     true layout class, confidence score, page, bbox, and clean text --
                     this is what Module 3 (chunking) reads for structure-aware chunking,
                     not the rendered markdown's formatting syntax
```

## Known simplifications (good class discussion / extension points)

- Reading order is a naive y-then-x sort — breaks on multi-column layouts.
- One 0.8B VLM does OCR, table-to-HTML, and figure captioning — small
  model, so expect rough edges on dense tables or long text blocks.
  Comparing its output against a dedicated OCR engine is a good exercise.
- No retrieval/embedding step yet — this module stops at clean markdown +
  metadata per document.

### Failure modes actually observed running this (not hypothetical)

Running the real samples (plus a synthetic one built via `make_sample_pdf.py`
during development, not included by default) surfaced concrete, reproducible
examples worth walking through in class -- the `annotated/` boxes make the
first one directly visible without needing to read any JSON:

- **Duplicate/overlapping boxes**: the layout detector sometimes emits two
  boxes over the same text with different class labels (e.g. `title` +
  `plain text`), so that line appears twice in the markdown. Visible directly
  in `annotated/page_001.png` for `federal_register_proclamation.pdf` -- look
  at "A Proclamation," which gets both a red `title` box and an overlapping
  blue `plain text` box. Confirmed again on `nasa_iss_factsheet.pdf` page 2
  (the running header gets both a `plain text` and an `abandon` box at the
  same location) -- this is a systematic detector behavior, not a one-off.
  No cross-class de-duplication (IoU-based NMS) is implemented — good
  candidate for a student exercise.
- **Chart numeric hallucination**: asked to describe a bar chart titled "Q3
  Regional Output" with values 40-80, the VLM's description said "Q5" and
  "40 to 80,000 units." The general gist (bar chart, four regions) was
  right; the specific numbers were confidently wrong. Classic small-VLM
  behavior on data-dense images. (Observed on the synthetic sample.)
- **Artifact type confusion**: a synthetic stamp/seal was described
  accurately ("red circular seal with APPROVED") but classified as `logo`
  instead of `stamp_seal` — the description was fine, the category label
  wasn't. The boundary between these types is genuinely fuzzy even when the
  description is correct. (Observed on the synthetic sample.)
- **Detector domain mismatch**: DocLayout-YOLO is trained mostly on academic
  papers (DocLayNet). A simple flat corporate-style logo got classified as
  `abandon` (page furniture) rather than `figure` on the synthetic sample --
  and the same thing happens on the real NASA logo in
  `nasa_iss_factsheet.pdf` (visible in `annotated/page_001.png` as a gray
  `abandon 0.84` box right next to the title). Either way it never reaches
  the VLM's artifact classifier — it only shows up in `metadata.json`'s
  `dropped_regions` (bbox + score, no description), not in
  `artifacts_detected`. Worth discussing as a real gap: a detector trained
  on one document style doesn't generalize perfectly to another.
- **Instruction-following isn't guaranteed**: the table-to-HTML prompt
  explicitly says "no markdown code fences" and the model wrapped its
  answer in ```` ```html ```` anyway. The pipeline strips it defensively
  (`vlm_client.table_to_html`), but it's a reminder that small local models
  don't reliably obey formatting constraints — don't trust prompt
  instructions to be load-bearing without a verification/cleanup step.
