from __future__ import annotations

from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OCR_OUTPUT_DIR = MODULE_DIR.parent / "1. OCR" / "output"
DEFAULT_REPORT_PATH = MODULE_DIR / "ocr_analysis_report.xlsx"

# Same model used for extraction in Module 1 -- token counts should reflect
# what that model actually saw, not a generic/approximate tokenizer.
TOKENIZER_MODEL_ID = "Qwen/Qwen3.5-0.8B"
