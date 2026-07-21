#!/usr/bin/env python3
"""
Train MiniGPT on a tiny char-level corpus.

Demonstrates TRAINING mode:
  - full sequence in one forward pass (parallel)
  - causal mask inside attention
  - next-token cross-entropy at every position (teacher forcing)

Usage:
  python train_tiny.py
  python train_tiny.py --steps 500 --d-model 256
"""

from __future__ import annotations

import argparse
import logging
import random
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from minimal_gpt import MiniGPT

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "tiny_corpus.txt"
CKPT_PATH = ROOT / "outputs" / "mini_gpt.pt"


TINY_CORPUS = """\
The cat sat on the mat.
The dog ran in the park.
Cats and dogs are animals.
The quick brown fox jumps over the lazy dog.
Transformers use self attention to mix token information.
Training runs in parallel with a causal mask.
Inference generates one token at a time.
KV cache stores past keys and values for speed.
"""


class CharDataset(Dataset):
    def __init__(self, text: str, seq_len: int) -> None:
        chars = sorted(set(text))
        self.stoi = {c: i for i, c in enumerate(chars)}
        self.itos = {i: c for c, i in self.stoi.items()}
        self.seq_len = seq_len
        self.data = torch.tensor([self.stoi[c] for c in text], dtype=torch.long)

    def __len__(self) -> int:
        return max(0, len(self.data) - self.seq_len - 1)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        chunk = self.data[idx : idx + self.seq_len + 1]
        x, y = chunk[:-1], chunk[1:]
        return x, y

    @property
    def vocab_size(self) -> int:
        return len(self.stoi)

    def decode(self, ids: torch.Tensor | list[int]) -> str:
        if isinstance(ids, torch.Tensor):
            ids = ids.tolist()
        return "".join(self.itos[i] for i in ids)


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def load_text() -> str:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(TINY_CORPUS, encoding="utf-8")
        log.info("Wrote default corpus to %s", DATA_PATH)
    return DATA_PATH.read_text(encoding="utf-8")


def train(args: argparse.Namespace) -> None:
    device = get_device()
    log.info("Device: %s", device)

    text = load_text()
    ds = CharDataset(text, seq_len=args.seq_len)
    dl = DataLoader(ds, batch_size=args.batch_size, shuffle=True, drop_last=True)

    model = MiniGPT(
        vocab_size=ds.vocab_size,
        n_layers=args.n_layers,
        n_heads=args.n_heads,
        d_model=args.d_model,
        d_ff=args.d_ff,
        max_seq_len=args.seq_len + 8,
        dropout=0.1,
    ).to(device)

    opt = torch.optim.AdamW(model.parameters(), lr=args.lr)
    pbar = tqdm(range(args.steps), desc="train")
    dl_iter = iter(dl)

    model.train()
    for step in pbar:
        try:
            x, y = next(dl_iter)
        except StopIteration:
            dl_iter = iter(dl)
            x, y = next(dl_iter)

        x, y = x.to(device), y.to(device)
        logits, _ = model(x, use_cache=False)
        loss = F.cross_entropy(logits.reshape(-1, ds.vocab_size), y.reshape(-1))

        opt.zero_grad(set_to_none=True)
        loss.backward()
        opt.step()

        pbar.set_postfix(loss=f"{loss.item():.3f}")

        if step == 0:
            log.info(
                "Training shape check: x=%s logits=%s (parallel over seq_len)",
                tuple(x.shape),
                tuple(logits.shape),
            )

    CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model": model.state_dict(),
            "config": {
                "vocab_size": ds.vocab_size,
                "n_layers": args.n_layers,
                "n_heads": args.n_heads,
                "d_model": args.d_model,
                "d_ff": args.d_ff,
                "max_seq_len": args.seq_len + 8,
            },
            "stoi": ds.stoi,
            "itos": {int(k): v for k, v in ds.itos.items()},
        },
        CKPT_PATH,
    )
    log.info("Saved checkpoint to %s", CKPT_PATH)

    model.eval()
    prompt = "The cat"
    start = torch.tensor(
        [[ds.stoi[c] for c in prompt]], dtype=torch.long, device=device
    )
    out = model.generate(start, max_new_tokens=40, use_cache=True)
    log.info("Sample (cached inference): %r", ds.decode(out[0]))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train tiny char-level MiniGPT")
    p.add_argument("--steps", type=int, default=300)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--seq-len", type=int, default=64)
    p.add_argument("--lr", type=float, default=3e-3)
    p.add_argument("--n-layers", type=int, default=4)
    p.add_argument("--n-heads", type=int, default=4)
    p.add_argument("--d-model", type=int, default=128)
    p.add_argument("--d-ff", type=int, default=512)
    return p.parse_args()


if __name__ == "__main__":
    train(parse_args())
