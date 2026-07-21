#!/usr/bin/env python3
"""
Minimal logit-lens demo on GPT-2 via TransformerLens.

Shows how each layer's residual stream projects to vocabulary predictions.
Requires: pip install transformer-lens

Usage:
  python logit_lens_demo.py
  python logit_lens_demo.py --prompt "The cat sat on the"
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from transformer_lens import HookedTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

OUT_DIR = Path(__file__).parent / "outputs"


def get_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def main(args: argparse.Namespace) -> None:
    device = get_device()
    log.info("Loading gpt2-small on %s", device)
    model = HookedTransformer.from_pretrained("gpt2-small", device=device)

    tokens = model.to_tokens(args.prompt)
    log.info("Prompt tokens: %s", model.to_str_tokens(tokens))

    _, cache = model.run_with_cache(tokens)
    n_layers = model.cfg.n_layers
    final_pos = tokens.shape[1] - 1

    rows: list[tuple[int, str, float]] = []
    for layer in range(n_layers):
        resid = cache[f"blocks.{layer}.hook_resid_post"][0, final_pos]
        logits = model.unembed(resid)
        probs = torch.softmax(logits, dim=-1)
        top_id = int(probs.argmax().item())
        top_tok = model.to_string(top_id)
        top_p = float(probs[top_id].item())
        rows.append((layer, top_tok, top_p))
        log.info("Layer %2d → top token: %10r  (p=%.3f)", layer, top_tok, top_p)

    layers = [r[0] for r in rows]
    conf = [r[2] for r in rows]
    labels = [r[1].replace("\n", "\\n") for r in rows]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(layers, conf, marker="o")
    ax.set_xlabel("Layer")
    ax.set_ylabel("Top-token probability at final position")
    ax.set_title(f'Logit lens: "{args.prompt}"')
    for x, y, lab in zip(layers, conf, labels, strict=True):
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7)
    fig.tight_layout()
    out_path = OUT_DIR / "logit_lens.png"
    fig.savefig(out_path, dpi=150)
    log.info("Saved plot to %s", out_path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", default="The cat sat on the")
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
