"""Step 2: page image -> classified region boxes (Doc Layout model)."""

from __future__ import annotations

from pathlib import Path

from huggingface_hub import hf_hub_download

from . import config
from .device import resolve_device

_MODEL = None
_REQUESTED_DEVICE = None  # set via configure(); None means "auto-pick best available"


def configure(device: str | None) -> None:
    """Call before the first detect_regions() to pin a specific device ('cpu'/'cuda'/'mps')."""
    global _REQUESTED_DEVICE
    _REQUESTED_DEVICE = device


def _load_model():
    global _MODEL
    if _MODEL is None:
        from doclayout_yolo import YOLOv10  # imported lazily: heavy, and pulls in ultralytics/torch

        weights_path = hf_hub_download(
            repo_id=config.LAYOUT_MODEL_REPO,
            filename=config.LAYOUT_MODEL_FILE,
        )
        _MODEL = YOLOv10(weights_path)
    return _MODEL


def detect_regions(page_image_path: Path) -> list[dict]:
    """Returns a list of {class, score, bbox: [x0, y0, x1, y1]} for one page image,
    sorted top-to-bottom, left-to-right (simple single-column reading order)."""
    model = _load_model()
    device = resolve_device(_REQUESTED_DEVICE)
    try:
        result = model.predict(
            str(page_image_path),
            imgsz=config.LAYOUT_IMGSZ,
            conf=config.LAYOUT_CONF_THRESHOLD,
            device=device,
            verbose=False,
        )[0]
    except (RuntimeError, NotImplementedError) as e:
        if device == "cpu":
            raise
        print(f"  [layout_detect] WARNING: predict() failed on {device} ({e!r}); falling back to cpu")
        result = model.predict(
            str(page_image_path),
            imgsz=config.LAYOUT_IMGSZ,
            conf=config.LAYOUT_CONF_THRESHOLD,
            device="cpu",
            verbose=False,
        )[0]

    names = result.names
    regions = []
    for box in result.boxes:
        x0, y0, x1, y1 = (float(v) for v in box.xyxy[0].tolist())
        regions.append(
            {
                "class": names[int(box.cls[0])],
                "score": round(float(box.conf[0]), 4),
                "bbox": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
            }
        )

    regions.sort(key=lambda r: (round(r["bbox"][1] / 20), r["bbox"][0]))
    return regions
