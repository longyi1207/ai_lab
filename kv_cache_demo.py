#!/usr/bin/env python3
"""
Compare inference WITH vs WITHOUT KV cache on HuggingFace GPT-2.

Shows the core inference optimization from notes/transformer_interview_visual.md §8.

Usage:
  python kv_cache_demo.py
  python kv_cache_demo.py --model gpt2 --new-tokens 32
"""

from __future__ import annotations

import argparse
import logging
import time

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


@torch.no_grad()
def generate_no_cache(
    model: AutoModelForCausalLM, input_ids: torch.Tensor, new_tokens: int
) -> tuple[torch.Tensor, float]:
    ids = input_ids.clone()
    t0 = time.perf_counter()
    for _ in range(new_tokens):
        out = model(ids, use_cache=False)
        next_id = out.logits[:, -1].argmax(dim=-1, keepdim=True)
        ids = torch.cat([ids, next_id], dim=1)
    elapsed = time.perf_counter() - t0
    return ids, elapsed


@torch.no_grad()
def generate_with_cache(
    model: AutoModelForCausalLM, input_ids: torch.Tensor, new_tokens: int
) -> tuple[torch.Tensor, float]:
    ids = input_ids.clone()
    past = None
    t0 = time.perf_counter()
    for step in range(new_tokens):
        ctx = ids if past is None else ids[:, -1:]
        out = model(ctx, past_key_values=past, use_cache=True)
        past = out.past_key_values
        next_id = out.logits[:, -1].argmax(dim=-1, keepdim=True)
        ids = torch.cat([ids, next_id], dim=1)
        if step == 0:
            n_layers = len(past) if past is not None else 0
            log.info(
                "KV cache: %d layers, each stores (K, V) tensors growing with seq_len",
                n_layers,
            )
    elapsed = time.perf_counter() - t0
    return ids, elapsed


def main(args: argparse.Namespace) -> None:
    device = get_device()
    log.info("Loading %s on %s", args.model, device)

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model).to(device)
    model.eval()

    prompt = args.prompt
    input_ids = tok(prompt, return_tensors="pt").input_ids.to(device)
    log.info("Prompt: %r (%d tokens)", prompt, input_ids.shape[1])

    _, t_no = generate_no_cache(model, input_ids, args.new_tokens)
    _, t_yes = generate_with_cache(model, input_ids, args.new_tokens)

    speedup = t_no / t_yes if t_yes > 0 else float("inf")
    log.info("---")
    log.info("Generate %d new tokens:", args.new_tokens)
    log.info("  WITHOUT cache: %.3fs  (recompute full prefix each step)", t_no)
    log.info("  WITH cache:    %.3fs  (append K/V only)", t_yes)
    log.info("  Speedup:       %.2fx", speedup)
    log.info(
        "Gap grows with seq_len because no-cache cost is ~O(n^2), cache is ~O(n) per step."
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="KV cache timing demo")
    p.add_argument("--model", default="gpt2")
    p.add_argument("--prompt", default="The cat sat on the")
    p.add_argument("--new-tokens", type=int, default=24)
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
