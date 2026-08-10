from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INPUT_DIR = ROOT_DIR / "input_pdfs"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "output"

RENDER_DPI = 200

# Layout detector: DocLayout-YOLO, trained on DocStructBench (DocLayNet + extra doc types)
LAYOUT_MODEL_REPO = "juliozhao/DocLayout-YOLO-DocStructBench"
LAYOUT_MODEL_FILE = "doclayout_yolo_docstructbench_imgsz1024.pt"
LAYOUT_IMGSZ = 1024
LAYOUT_CONF_THRESHOLD = 0.25  # regions below this are still kept but flagged for review

# Vision-language model used for all per-region content extraction
VLM_MODEL_ID = "Qwen/Qwen3.5-0.8B"
VLM_MAX_NEW_TOKENS_TEXT = 512
VLM_MAX_NEW_TOKENS_TABLE = 1024

# DocLayout-YOLO class names -> how we route them
TITLE_CLASSES = {"title"}
BODY_TEXT_CLASSES = {"plain text"}
CAPTION_CLASSES = {"figure_caption", "table_caption", "table_footnote", "formula_caption"}
TABLE_CLASSES = {"table"}
FIGURE_CLASSES = {"figure"}
FORMULA_CLASSES = {"isolate_formula"}
DROP_CLASSES = {"abandon"}  # headers/footers/watermarks: logged, not put in markdown body

# Figure sub-types the VLM is asked to classify each "figure" region into.
# chart/photo/diagram go into the markdown body; the rest are treated as
# document artifacts and only recorded in metadata.
CONTENT_FIGURE_TYPES = {"chart", "photo", "diagram", "other"}
ARTIFACT_FIGURE_TYPES = {"logo", "signature", "stamp_seal"}
