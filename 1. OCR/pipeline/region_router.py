"""Step 4: crop each detected region and route it to the right handler by class."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from . import config, vlm_client


def crop_region(page_image: Image.Image, bbox: list[float]) -> Image.Image:
    x0, y0, x1, y1 = bbox
    return page_image.crop((int(x0), int(y0), int(x1), int(y1)))


def handle_region(region: dict, page_image: Image.Image, page_num: int, region_idx: int, images_dir: Path) -> dict:
    """Returns a dict describing what to put in the markdown (may be empty) and
    any metadata to log (artifacts, dropped regions, low-confidence flags)."""
    cls = region["class"]
    crop = crop_region(page_image, region["bbox"])

    result = {
        "page": page_num,
        "class": cls,
        "score": region["score"],
        "bbox": region["bbox"],
        "markdown": "",
        "text": "",  # same content as markdown, without the decoration (##, *, backticks) -- for
                     # anything downstream that wants the true layout class + clean text, not
                     # markdown syntax to regex back apart (see Module 3's layout_blocks.py)
        "artifact": None,
        "low_confidence": region["score"] < config.LAYOUT_CONF_THRESHOLD + 0.15,
    }

    if cls in config.DROP_CLASSES:
        result["dropped"] = True
        return result

    if cls in config.TITLE_CLASSES:
        text = vlm_client.ocr_text(crop)
        result["markdown"] = f"## {text}\n"
        result["text"] = text

    elif cls in config.BODY_TEXT_CLASSES:
        text = vlm_client.ocr_text(crop)
        result["markdown"] = f"{text}\n"
        result["text"] = text

    elif cls in config.CAPTION_CLASSES:
        text = vlm_client.ocr_text(crop)
        result["markdown"] = f"*{text}*\n"
        result["text"] = text

    elif cls in config.TABLE_CLASSES:
        html = vlm_client.table_to_html(crop)
        result["markdown"] = f"\n{html}\n"
        result["text"] = html

    elif cls in config.FORMULA_CLASSES:
        text = vlm_client.ocr_text(crop)
        result["markdown"] = f"`{text}`\n"
        result["text"] = text

    elif cls in config.FIGURE_CLASSES:
        info = vlm_client.describe_figure(crop)
        if info["type"] in config.ARTIFACT_FIGURE_TYPES:
            result["artifact"] = {
                "page": page_num,
                "type": info["type"],
                "description": info["description"],
                "bbox": region["bbox"],
            }
        else:
            img_name = f"page{page_num:03d}_region{region_idx:03d}.png"
            images_dir.mkdir(parents=True, exist_ok=True)
            crop.save(images_dir / img_name)
            result["markdown"] = (
                f"\n![{info['type']}](images/{img_name})\n\n*{info['description']}*\n"
            )
            result["text"] = info["description"]
            result["extra"] = {"path": f"images/{img_name}", "figure_type": info["type"]}

    else:
        # Unknown class from the layout model: OCR it as plain text rather than silently dropping it.
        text = vlm_client.ocr_text(crop)
        result["markdown"] = f"{text}\n"
        result["text"] = text

    return result
