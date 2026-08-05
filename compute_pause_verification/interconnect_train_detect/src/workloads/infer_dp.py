"""Benign multi-process inference — HF-safe forward/generate."""
from __future__ import annotations

import argparse

import torch
import torch.distributed as dist

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("infer_dp")


def run(
    model_cfg: dict,
    steps: int,
    batch_size: int,
    seq_len: int,
    max_new: int = 8,
    workload_name: str = "infer_dp",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        mon.set_synth_mode("infer")
        mon.marker(workload_name, "start", world_size=world, steps=steps)

    model = build_model(model_cfg).to(device)
    model.eval()
    vocab = vocab_size_of(model, model_cfg)

    with torch.no_grad():
        for step in range(steps):
            x, _ = random_batch(batch_size, seq_len, vocab, device)
            if hasattr(model, "generate"):
                _ = model.generate(x[:, : max(1, seq_len // 2)], max_new=max_new)
            else:
                _ = model(x)
            if world > 1:
                t = torch.tensor([float(step)], device=device)
                dist.all_reduce(t, op=dist.ReduceOp.SUM)
            if is_main(rank) and step % 5 == 0:
                mon.marker(workload_name, "step", step=step)

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("infer_dp done steps=%d world=%d", steps, world)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--max-new", type=int, default=8)
    ap.add_argument("--name", default="infer_dp")
    args = ap.parse_args()

    model_cfg = {
        "backend": "tiny",
        "n_layer": 4, "n_head": 4, "n_embd": 128,
        "vocab_size": 256, "block_size": max(args.seq_len, 64),
    }
    if args.config:
        cfg = load_config(args.config)
        model_cfg = {**model_cfg, **cfg.get("model", {})}
        for w in cfg.get("workloads", []):
            if w.get("kind") == "infer_dp":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)

    run(model_cfg, args.steps, args.batch_size, args.seq_len, args.max_new, args.name)


if __name__ == "__main__":
    main()
