"""Benign data-parallel training — fat all-reduce every step + NCCL byte accounting."""
from __future__ import annotations

import argparse
import os
import time

import torch
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("train_ddp")


def run(
    model_cfg: dict,
    steps: int,
    warmup: int,
    batch_size: int,
    seq_len: int,
    lr: float = 3e-4,
    workload_name: str = "train_ddp",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("train")
        mon.marker(workload_name, "start", world_size=world, steps=steps)

    model = build_model(model_cfg).to(device)
    raw = model
    if world > 1:
        model = DDP(model)
        nccl_hook.install_ddp_comm_hook(model)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    vocab = vocab_size_of(raw if not hasattr(model, "module") else model.module, model_cfg)

    for step in range(steps):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        # if no comm hook (world==1 or hook failed), estimate
        if world == 1 or not hasattr(model, "register_comm_hook"):
            for p in (model.module if hasattr(model, "module") else model).parameters():
                if p.grad is not None:
                    nccl_hook.record_bytes(int(p.grad.numel() * p.grad.element_size()))
        opt.step()
        if is_main(rank) and step >= warmup and step % 5 == 0:
            mon.marker(workload_name, "step", step=step, loss=float(loss.detach()))
            nccl_hook.maybe_emit_event(mon, 0, op="AllReduce")
        if world > 1:
            dist.barrier()

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("train_ddp done steps=%d world=%d device=%s", steps, world, device)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--warmup-steps", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--name", default="train_ddp")
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
            if w.get("kind") == "train_ddp":
                args.steps = w.get("steps", args.steps)
                args.warmup_steps = w.get("warmup_steps", args.warmup_steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)

    t0 = time.time()
    run(model_cfg, args.steps, args.warmup_steps, args.batch_size, args.seq_len, args.lr, args.name)
    if int(os.environ.get("RANK", "0")) == 0:
        log.info("wall=%.2fs", time.time() - t0)


if __name__ == "__main__":
    main()
