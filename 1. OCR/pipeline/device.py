"""Shared accelerator device selection for both the layout detector and the VLM.

Deliberately explicit rather than silently defaulting to CPU: students should see
which backend (CUDA / Apple MPS / CPU) actually ran the model, and see what happens
when a requested device isn't available or a specific op isn't supported on it.
"""

from __future__ import annotations

import torch

VALID_DEVICES = {"cpu", "cuda", "mps"}


def resolve_device(preferred: str | None = None) -> str:
    """Returns 'cuda', 'mps', or 'cpu'.

    If preferred is given, it is validated against actual hardware availability
    and an explicit error is raised if it can't be honored -- better than pytorch's
    own late, cryptic failure the first time a tensor hits the wrong backend.
    If preferred is None, picks the best available: cuda > mps > cpu.
    """
    if preferred is not None:
        if preferred not in VALID_DEVICES:
            raise ValueError(f"Unknown device '{preferred}', expected one of {sorted(VALID_DEVICES)}")
        if preferred == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("Requested device 'cuda' but no CUDA GPU is available on this machine.")
        if preferred == "mps" and not torch.backends.mps.is_available():
            raise RuntimeError("Requested device 'mps' but the Apple MPS backend is not available on this machine.")
        return preferred

    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"
