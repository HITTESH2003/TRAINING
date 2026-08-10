"""
Module 1: Data Processing — CLI entrypoint.

Steps per PDF (see pipeline/ for each one):
  1. pdf_to_images  : render pages to PNG
  2. layout_detect  : classify regions per page (Doc Layout model)
                      -> visualize.save_annotated() draws the boxes + labels
                         straight away, before any VLM call happens
  3. vlm_client     : OCR text / table -> HTML / figure -> description (Qwen3.5-0.8B)
  4. region_router  : crop + dispatch each region by class
  5. assemble       : reading-order markdown
  6. postprocess    : cleaning & validation
  7. metadata       : PDF + derived metadata JSON, and regions.json -- the full
                      per-region layout record (true class, score, bbox, text)
                      for every region that reached the markdown body

Usage:
  python run_pipeline.py                       # process every PDF in input_pdfs/
  python run_pipeline.py --input some.pdf       # process a single PDF
  python run_pipeline.py --input some_folder/   # process every PDF in a given folder
  python run_pipeline.py --output custom_out/   # write elsewhere
  python run_pipeline.py --device cpu           # force a specific backend (cpu/cuda/mps)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image

from pipeline import assemble, config, layout_detect, metadata, pdf_to_images, postprocess, region_router, visualize, vlm_client
from pipeline.device import resolve_device


def process_pdf(pdf_path: Path, output_dir: Path) -> None:
    doc_out_dir = output_dir / pdf_path.stem
    pages_dir = doc_out_dir / "pages"
    images_dir = doc_out_dir / "images"
    annotated_dir = doc_out_dir / "annotated"

    print(f"\n=== {pdf_path.name} ===")

    print("  [1/7] rendering pages to images...")
    page_paths = pdf_to_images.render_pdf_pages(pdf_path, pages_dir, config.RENDER_DPI)
    pdf_meta = pdf_to_images.read_pdf_metadata(pdf_path)
    print(f"        {len(page_paths)} page(s) rendered at {config.RENDER_DPI} DPI")

    all_regions = []
    artifacts = []
    page_markdowns = []

    for page_num, page_path in enumerate(page_paths, start=1):
        print(f"  [2/7] page {page_num}: detecting layout regions...")
        regions = layout_detect.detect_regions(page_path)
        print(f"        {len(regions)} region(s) found")

        page_image = Image.open(page_path).convert("RGB")
        visualize.save_annotated(page_image, regions, annotated_dir / f"page_{page_num:03d}.png")

        region_results = []
        print(f"  [3-4/7] page {page_num}: extracting content per region (VLM)...")
        for region_idx, region in enumerate(regions, start=1):
            result = region_router.handle_region(region, page_image, page_num, region_idx, images_dir)
            region_results.append(result)
            if result.get("artifact"):
                artifacts.append(result["artifact"])

        all_regions.extend(region_results)
        page_markdowns.append(assemble.build_page_markdown(page_num, region_results))

    print("  [5/7] assembling markdown...")
    raw_markdown = assemble.build_document_markdown(pdf_path.stem, page_markdowns)

    print("  [6/7] post-processing (validation & cleaning)...")
    clean = postprocess.clean_markdown(raw_markdown)
    malformed_tables = postprocess.find_malformed_tables(clean)
    if malformed_tables:
        print(f"        WARNING: {len(malformed_tables)} malformed table(s) found, kept as-is for review")

    print("  [7/7] writing metadata...")
    doc_metadata = metadata.build_metadata(pdf_meta, all_regions, artifacts, malformed_tables)
    regions_export = metadata.build_regions_export(all_regions)

    doc_out_dir.mkdir(parents=True, exist_ok=True)
    (doc_out_dir / f"{pdf_path.stem}.md").write_text(clean, encoding="utf-8")
    (doc_out_dir / "metadata.json").write_text(json.dumps(doc_metadata, indent=2), encoding="utf-8")
    (doc_out_dir / "regions.json").write_text(json.dumps(regions_export, indent=2), encoding="utf-8")

    print(f"  done -> {doc_out_dir}")


def collect_pdfs(input_path: Path) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            sys.exit(f"Not a PDF: {input_path}")
        return [input_path]
    if input_path.is_dir():
        pdfs = sorted(input_path.glob("*.pdf"))
        if not pdfs:
            sys.exit(f"No PDFs found in {input_path}")
        return pdfs
    sys.exit(f"Input path does not exist: {input_path}")


def main():
    parser = argparse.ArgumentParser(description="PDF -> markdown (text + HTML tables + figure descriptions) + metadata JSON")
    parser.add_argument("--input", type=Path, default=config.DEFAULT_INPUT_DIR, help="PDF file or folder of PDFs (default: input_pdfs/)")
    parser.add_argument("--output", type=Path, default=config.DEFAULT_OUTPUT_DIR, help="output folder (default: output/)")
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "mps"],
        default=None,
        help="force a specific backend; default auto-picks the best available (cuda > mps > cpu)",
    )
    args = parser.parse_args()

    pdfs = collect_pdfs(args.input)
    args.output.mkdir(parents=True, exist_ok=True)

    resolved_device = resolve_device(args.device)
    print(f"Using device: {resolved_device}" + (" (auto-selected)" if args.device is None else " (forced via --device)"))
    layout_detect.configure(args.device)
    vlm_client.configure(args.device)

    print(f"Found {len(pdfs)} PDF(s) to process. Output -> {args.output}")
    for pdf_path in pdfs:
        process_pdf(pdf_path, args.output)

    print(f"\nAll done. {len(pdfs)} document(s) processed -> {args.output}")


if __name__ == "__main__":
    main()
