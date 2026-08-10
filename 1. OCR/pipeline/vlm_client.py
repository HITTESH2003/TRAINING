"""Step 3: cropped region image -> text / table HTML / figure description,
via the small vision-language model (Qwen3.5-0.8B)."""

from __future__ import annotations

from PIL import Image

from . import config
from .device import resolve_device

_PROCESSOR = None
_MODEL = None
_REQUESTED_DEVICE = None  # set via configure(); None means "auto-pick best available"


def configure(device: str | None) -> None:
    """Call before the first _load() to pin a specific device ('cpu'/'cuda'/'mps')."""
    global _REQUESTED_DEVICE
    _REQUESTED_DEVICE = device


def _load():
    global _PROCESSOR, _MODEL
    if _MODEL is None:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        device = resolve_device(_REQUESTED_DEVICE)
        print(f"  [vlm_client] loading {config.VLM_MODEL_ID} on device: {device}")
        _PROCESSOR = AutoProcessor.from_pretrained(config.VLM_MODEL_ID)
        _MODEL = AutoModelForImageTextToText.from_pretrained(config.VLM_MODEL_ID).to(device)
    return _PROCESSOR, _MODEL


def _ask(image: Image.Image, prompt: str, max_new_tokens: int) -> str:
    processor, model = _load()
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(model.device)

    try:
        output = model.generate(**inputs, max_new_tokens=max_new_tokens)
    except (RuntimeError, NotImplementedError) as e:
        if model.device.type == "cpu":
            raise
        # Some ops aren't implemented on every backend (e.g. certain MPS kernels).
        # Fall back to CPU once, loudly, rather than crash the whole batch.
        print(f"  [vlm_client] WARNING: generate() failed on {model.device} ({e!r}); falling back to cpu")
        global _MODEL
        _MODEL = model.to("cpu")
        inputs = inputs.to("cpu")
        output = _MODEL.generate(**inputs, max_new_tokens=max_new_tokens)

    generated = output[0][inputs["input_ids"].shape[-1]:]
    return processor.decode(generated, skip_special_tokens=True).strip()


def ocr_text(image: Image.Image) -> str:
    return _ask(
        image,
        "Transcribe all text in this image exactly as written. "
        "Return plain text only, no commentary, no markdown formatting.",
        config.VLM_MAX_NEW_TOKENS_TEXT,
    )


def table_to_html(image: Image.Image) -> str:
    raw = _ask(
        image,
        "Convert this table image into a single valid HTML <table> element, "
        "preserving all rows, columns and header cells. "
        "Return only the HTML markup, no markdown code fences, no commentary.",
        config.VLM_MAX_NEW_TOKENS_TABLE,
    )
    # The model doesn't always follow the "no code fences" instruction -- strip
    # a ```html ... ``` or ``` ... ``` wrapper if it added one anyway.
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def describe_figure(image: Image.Image) -> dict:
    """Classifies a 'figure' region and describes it in one VLM call.
    Returns {"type": one of config.CONTENT_FIGURE_TYPES | ARTIFACT_FIGURE_TYPES, "description": str}."""
    raw = _ask(
        image,
        "This image is cropped from a document page. "
        "Classify it as exactly one of: chart, photo, diagram, logo, signature, stamp_seal, other. "
        "Then write a one-sentence description of what it shows. "
        "Reply in exactly this format:\nTYPE: <type>\nDESCRIPTION: <description>",
        config.VLM_MAX_NEW_TOKENS_TEXT,
    )
    return _parse_figure_reply(raw)


def _parse_figure_reply(raw: str) -> dict:
    fig_type = "other"
    description = raw.strip()
    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("TYPE:"):
            candidate = line.split(":", 1)[1].strip().lower()
            valid = config.CONTENT_FIGURE_TYPES | config.ARTIFACT_FIGURE_TYPES
            fig_type = candidate if candidate in valid else "other"
        elif line.upper().startswith("DESCRIPTION:"):
            description = line.split(":", 1)[1].strip()
    return {"type": fig_type, "description": description}
