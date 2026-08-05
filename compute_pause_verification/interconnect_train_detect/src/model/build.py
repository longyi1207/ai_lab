"""Build model from config dict — tiny GPT or HuggingFace CausalLM."""
from __future__ import annotations

from typing import Any

import torch
import torch.nn as nn

from .tiny_gpt import TinyConfig, TinyGPT


class HFCausalWrapper(nn.Module):
    """Uniform API: forward(idx, targets=None) -> (logits, loss); generate(...)."""

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model
        self.config = getattr(model, "config", None)

    def forward(self, idx: torch.Tensor, targets: torch.Tensor | None = None):
        if targets is not None:
            out = self.model(input_ids=idx, labels=targets)
            return out.logits, out.loss
        out = self.model(input_ids=idx)
        return out.logits, None

    @torch.no_grad()
    def generate(self, idx: torch.Tensor, max_new: int = 16) -> torch.Tensor:
        return self.model.generate(idx, max_new_tokens=max_new, do_sample=True)


def build_model(cfg: dict[str, Any]) -> nn.Module:
    backend = cfg.get("backend", "tiny")
    if backend == "hf":
        try:
            from transformers import AutoModelForCausalLM
        except ImportError as e:
            raise ImportError("pip install transformers for model.backend: hf") from e
        dtype_key = cfg.get("dtype", "bf16")
        torch_dtype = {
            "bf16": torch.bfloat16,
            "bfloat16": torch.bfloat16,
            "fp16": torch.float16,
            "float16": torch.float16,
            "fp32": torch.float32,
            "float32": torch.float32,
        }.get(dtype_key, torch.bfloat16)
        raw = AutoModelForCausalLM.from_pretrained(
            cfg["name_or_path"],
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        )
        return HFCausalWrapper(raw)

    # tiny (default) — also if legacy configs only have n_embd fields
    if backend in (None, "tiny") or ("n_embd" in cfg and backend != "hf"):
        return TinyGPT(TinyConfig.from_dict(cfg))
    raise ValueError(f"unknown model backend: {backend}")


def vocab_size_of(model: nn.Module, cfg: dict[str, Any]) -> int:
    if isinstance(model, TinyGPT):
        return model.cfg.vocab_size
    if isinstance(model, HFCausalWrapper) and model.config is not None:
        return int(getattr(model.config, "vocab_size", cfg.get("vocab_size", 32000)))
    return int(cfg.get("vocab_size", 32000))
