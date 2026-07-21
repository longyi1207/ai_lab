"""Load a checkpoint and generate text — the qualitative sanity check that a loss number alone
doesn't give you. Usage: .venv/bin/python src/sample.py [--ckpt_dir checkpoints/shakespeare_gpt]
"""

import argparse
from pathlib import Path

import tiktoken
import torch

from config import ModelConfig
from model import GPT
from utils import load_checkpoint, select_device, DistState


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt_dir", type=str, default="checkpoints/shakespeare_gpt")
    parser.add_argument("--prompt", type=str, default="ROMEO:")
    parser.add_argument("--max_new_tokens", type=int, default=200)
    parser.add_argument("--temperature", type=float, default=0.8)
    parser.add_argument("--top_k", type=int, default=100)
    args = parser.parse_args()

    device = select_device(DistState())
    ckpt = load_checkpoint(args.ckpt_dir, device)
    if ckpt is None:
        raise FileNotFoundError(f"No checkpoint found in {args.ckpt_dir}")

    model_cfg = ModelConfig(**ckpt["model_config"])
    model = GPT(model_cfg).to(device)
    model.load_state_dict(ckpt["model_state_dict"])
    model.eval()

    enc = tiktoken.get_encoding("gpt2")
    idx = torch.tensor([enc.encode_ordinary(args.prompt)], dtype=torch.long, device=device)

    print(f"--- checkpoint step {ckpt['step']} ---")
    print(f"--- prompt: {args.prompt!r} ---\n")
    out = model.generate(idx, args.max_new_tokens, temperature=args.temperature, top_k=args.top_k)
    print(enc.decode(out[0].tolist()))


if __name__ == "__main__":
    main()
