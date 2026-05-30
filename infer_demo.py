#!/usr/bin/env python3
"""
Side-by-side TRAINING vs INFERENCE on a trained MiniGPT checkpoint.

Usage:
  python train_tiny.py          # first
  python infer_demo.py
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import torch
import torch.nn.functional as F

from minimal_gpt import MiniGPT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

CKPT_PATH = Path(__file__).parent / "outputs" / "mini_gpt.pt"


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_model(device: torch.device) -> tuple[MiniGPT, dict]:
    if not CKPT_PATH.exists():
        raise FileNotFoundError(
            f"No checkpoint at {CKPT_PATH}. Run: python train_tiny.py"
        )
    ckpt = torch.load(CKPT_PATH, map_location=device, weights_only=False)
    cfg = ckpt["config"]
    model = MiniGPT(**cfg).to(device)
    model.load_state_dict(ckpt["model"])
    model.eval()
    return model, ckpt


def decode(ids: torch.Tensor, itos: dict[int, str]) -> str:
    return "".join(itos[int(i)] for i in ids.tolist())


def demo_training_forward(
    model: MiniGPT,
    prompt: str,
    stoi: dict[str, int],
    itos: dict[int, str],
    device: torch.device,
) -> None:
    ids = torch.tensor([[stoi[c] for c in prompt]], device=device)
    with torch.no_grad():
        logits, _ = model(ids, use_cache=False)
        preds = logits.argmax(dim=-1)
        loss = F.cross_entropy(
            logits[:, :-1].reshape(-1, logits.size(-1)),
            ids[:, 1:].reshape(-1),
        )
    log.info("=== TRAINING MODE (one parallel forward) ===")
    log.info("Input tokens:  %s", ids.shape)
    log.info("Logits:        %s  ← all positions at once", tuple(logits.shape))
    log.info("Next-token loss (teacher forcing): %.3f", loss.item())
    log.info("Argmax next-token at each position: %r", decode(preds[0], itos))


def demo_inference(
    model: MiniGPT,
    prompt: str,
    stoi: dict[str, int],
    itos: dict[int, str],
    device: torch.device,
    new_tokens: int,
) -> None:
    ids = torch.tensor([[stoi[c] for c in prompt]], device=device)
    log.info("=== INFERENCE MODE (serial, one token per step) ===")
    log.info("Step 0 prefix: %r", decode(ids[0], itos))

    caches = None
    for step in range(new_tokens):
        ctx = ids[:, -1:] if caches is not None else ids
        with torch.no_grad():
            logits, caches = model(ctx, past_caches=caches, use_cache=True)
        next_id = logits[:, -1].argmax(dim=-1, keepdim=True)
        ids = torch.cat([ids, next_id], dim=1)
        log.info(
            "Step %d: appended %r → %r",
            step + 1,
            itos[int(next_id.item())],
            decode(ids[0], itos),
        )


def main(args: argparse.Namespace) -> None:
    device = get_device()
    model, ckpt = load_model(device)
    stoi = ckpt["stoi"]
    itos = {int(k): v for k, v in ckpt["itos"].items()}

    for c in args.prompt:
        if c not in stoi:
            raise ValueError(f"Char {c!r} not in training vocab")

    demo_training_forward(model, args.prompt, stoi, itos, device)
    log.info("")
    demo_inference(model, args.prompt, stoi, itos, device, args.new_tokens)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt", default="The cat")
    p.add_argument("--new-tokens", type=int, default=8)
    return p.parse_args()


if __name__ == "__main__":
    main(parse_args())
