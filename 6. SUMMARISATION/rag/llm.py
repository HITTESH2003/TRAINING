"""Qwen3-0.6B summarization, with correct handling of two real model-config
details from the model's own card:

1. enable_thinking: Qwen3 models can emit a <think>...</think> reasoning
   block before the actual answer. It's controlled at prompt-build time
   (apply_chat_template(..., enable_thinking=...)), not at generation time --
   toggling it changes what the model is asked to produce, not just how the
   output is parsed afterward.

2. Sampling parameters are officially DIFFERENT for thinking vs non-thinking
   mode (see config.GENERATION_PRESETS) -- using one generic temperature for
   both is a real, common mistake this module avoids on purpose.

Thinking content is separated from the final answer using the model card's
own documented method: find token id 151668 (</think>) in the generated
ids and split there, not a string search on the decoded text.
"""

from __future__ import annotations

import time

from . import config

_THINK_END_TOKEN_ID = 151668  # </think>, per the Qwen3 model card

_TOKENIZER = None
_MODEL = None


def _resolve_device() -> str:
    import torch

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _load():
    global _TOKENIZER, _MODEL
    if _MODEL is None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = _resolve_device()
        print(f"  [llm] loading {config.LLM_MODEL_ID} on device: {device}")
        _TOKENIZER = AutoTokenizer.from_pretrained(config.LLM_MODEL_ID)
        _MODEL = AutoModelForCausalLM.from_pretrained(config.LLM_MODEL_ID, torch_dtype="auto").to(device)
    return _TOKENIZER, _MODEL


def count_prompt_tokens(messages: list[dict], enable_thinking: bool = True) -> int:
    tokenizer, _ = _load()
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=enable_thinking)
    return len(tokenizer(text, add_special_tokens=False)["input_ids"])


def generate(
    messages: list[dict],
    enable_thinking: bool = True,
    max_new_tokens: int = config.DEFAULT_MAX_NEW_TOKENS,
    generation_overrides: dict | None = None,
) -> dict:
    tokenizer, model = _load()
    params = dict(config.GENERATION_PRESETS[enable_thinking])
    if generation_overrides:
        params.update(generation_overrides)

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=enable_thinking)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)
    prompt_token_count = inputs["input_ids"].shape[-1]

    start = time.perf_counter()
    generated = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=True,
        temperature=params["temperature"],
        top_p=params["top_p"],
        top_k=params["top_k"],
    )
    generation_time_s = time.perf_counter() - start

    output_ids = generated[0][prompt_token_count:].tolist()

    try:
        split_index = len(output_ids) - output_ids[::-1].index(_THINK_END_TOKEN_ID)
        thinking_ids, answer_ids = output_ids[:split_index], output_ids[split_index:]
    except ValueError:
        thinking_ids, answer_ids = [], output_ids

    thinking_text = tokenizer.decode(thinking_ids, skip_special_tokens=True).strip()
    answer_text = tokenizer.decode(answer_ids, skip_special_tokens=True).strip()

    return {
        "answer": answer_text,
        "thinking": thinking_text,
        "prompt_token_count": prompt_token_count,
        "output_token_count": len(output_ids),
        "generation_time_s": round(generation_time_s, 2),
        "enable_thinking": enable_thinking,
        "generation_params": params,
    }
