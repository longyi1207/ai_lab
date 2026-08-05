"""Column-parallel MLP tensor-parallel inference (real collectives, not just footprint).

Each TP rank owns a shard of the MLP up-projection; all-gather output activations.
Still not full Megatron attention TP — enough to generate training-like east-west traffic.
"""
from __future__ import annotations

import argparse

import torch
import torch.distributed as dist
import torch.nn as nn
import torch.nn.functional as F

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("infer_tp")


class ColumnParallelLinear(nn.Module):
    def __init__(self, in_f: int, out_f: int, tp_rank: int, tp_size: int):
        super().__init__()
        assert out_f % tp_size == 0
        self.out_local = out_f // tp_size
        self.tp_rank = tp_rank
        self.tp_size = tp_size
        self.weight = nn.Parameter(torch.randn(self.out_local, in_f) * 0.02)

    def forward(self, x: torch.Tensor, group=None) -> torch.Tensor:
        # x: (B, T, in) → local (B, T, out_local) → all-gather → (B, T, out)
        local = F.linear(x, self.weight)
        if self.tp_size == 1 or not dist.is_initialized():
            return local
        chunks = [torch.empty_like(local) for _ in range(self.tp_size)]
        dist.all_gather(chunks, local, group=group)
        nccl_hook.record_bytes(int(local.numel() * local.element_size()) * self.tp_size)
        return torch.cat(chunks, dim=-1)


def run(
    model_cfg: dict,
    steps: int,
    batch_size: int,
    seq_len: int,
    tp_size: int = 2,
    workload_name: str = "infer_tp",
) -> None:
    rank, world, _, device = dist_setup()
    if world % tp_size != 0:
        raise ValueError(f"world {world} not divisible by tp_size {tp_size}")

    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")
        mon.marker(workload_name, "start", world_size=world, tp_size=tp_size)

    model = build_model(model_cfg).to(device)
    model.eval()
    hidden = int(model_cfg.get("n_embd", 128))
    vocab = vocab_size_of(model, model_cfg)

    group = None
    tp_rank = 0
    if world > 1:
        groups = []
        for g in range(world // tp_size):
            ranks = list(range(g * tp_size, (g + 1) * tp_size))
            groups.append(dist.new_group(ranks=ranks))
        group = groups[rank // tp_size]
        tp_rank = rank % tp_size

    # TP MLP layer used every step (activation all-gather)
    cp = ColumnParallelLinear(hidden, 4 * hidden, tp_rank, tp_size).to(device)

    with torch.no_grad():
        for step in range(steps):
            x, _ = random_batch(batch_size, seq_len, vocab, device)
            logits, _ = model(x)
            # take last-hidden proxy from logits projection input — use random act of hidden
            act = torch.randn(batch_size, seq_len, hidden, device=device, dtype=logits.dtype)
            _ = cp(act, group=group)
            if is_main(rank) and step % 5 == 0:
                mon.marker(workload_name, "step", step=step)
                nccl_hook.maybe_emit_event(mon, 0, op="AllGather")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("infer_tp done (column-parallel MLP all-gather)")
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=1)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--tp-size", type=int, default=2)
    ap.add_argument("--name", default="infer_tp")
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
            if w.get("kind") == "infer_tp":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.tp_size = w.get("tp_size", args.tp_size)

    run(model_cfg, args.steps, args.batch_size, args.seq_len, args.tp_size, args.name)


if __name__ == "__main__":
    main()
