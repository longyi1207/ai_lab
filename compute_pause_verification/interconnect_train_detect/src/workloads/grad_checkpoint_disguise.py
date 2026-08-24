"""Gradient-checkpointing adversarial workload — round #2 on the memory
axis (see docs/REDTEAM.md), a more realistic technique than shrinking
batch/seq (which risked pushing power out of the classifier's trained
region, rounds 10-11/14). Real large-model training uses activation
checkpointing routinely to fit bigger models/batches in memory: instead of
storing every transformer block's intermediate activations for the
backward pass, only the block's INPUT is kept and the forward is
recomputed during backward. Trades ~30-40% more compute for meaningfully
less activation memory, at REALISTIC batch/seq (unlike rounds 10-11).

Wraps `TinyGPT.blocks` (a public `nn.ModuleList`, see src/model/tiny_gpt.py)
from the outside via `torch.utils.checkpoint.checkpoint` — no edits to
tiny_gpt.py. Only supports the tiny backend (accesses `.blocks`/`.tok_emb`/
etc. directly, same assumption low_mem_disguise.py and friends make about
not using a DDP wrapper); an HF backend would need
`model.gradient_checkpointing_enable()` instead, a different code path,
out of scope here.

Combined with the SGD/momentum=0 fix (proven partial win) and the plain
unchunked AllReduce (no communication-shape changes, which backfired
repeatedly).
"""
from __future__ import annotations

import argparse

import torch
import torch.distributed as dist
import torch.nn.functional as F
import torch.utils.checkpoint

from ..model.tiny_gpt import TinyConfig, TinyGPT
from ..model.build import vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("grad_checkpoint_disguise")


def checkpointed_forward(model: TinyGPT, idx: torch.Tensor, targets: torch.Tensor | None = None):
    B, T = idx.shape
    if T > model.cfg.block_size:
        raise ValueError(f"seq {T} > block_size {model.cfg.block_size}")
    pos = torch.arange(T, device=idx.device)
    x = model.drop(model.tok_emb(idx) + model.pos_emb(pos))
    for blk in model.blocks:
        x = torch.utils.checkpoint.checkpoint(blk, x, use_reentrant=False)
    logits = model.head(model.ln_f(x))
    loss = None
    if targets is not None:
        loss = F.cross_entropy(logits.view(-1, logits.size(-1)), targets.view(-1))
    return logits, loss


def unchunked_grad_sync(model: torch.nn.Module) -> None:
    if not dist.is_initialized() or dist.get_world_size() == 1:
        return
    world = dist.get_world_size()
    for p in model.parameters():
        if p.grad is None:
            continue
        dist.all_reduce(p.grad, op=dist.ReduceOp.SUM)
        p.grad /= world
        nccl_hook.record_bytes(int(p.grad.numel() * p.grad.element_size()) * 2)


def run(
    model_cfg: dict,
    steps: int,
    batch_size: int,
    seq_len: int,
    lr: float = 3e-4,
    workload_name: str = "grad_checkpoint_disguise",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")
        mon.marker(workload_name, "start", world_size=world)

    if model_cfg.get("backend", "tiny") != "tiny":
        raise ValueError("grad_checkpoint_disguise only supports model.backend: tiny (see module docstring)")
    model = TinyGPT(TinyConfig.from_dict(model_cfg)).to(device)
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.0)
    vocab = vocab_size_of(model, model_cfg)

    for step in range(steps):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        opt.zero_grad(set_to_none=True)
        _, loss = checkpointed_forward(model, x, y)
        loss.backward()
        unchunked_grad_sync(model)
        opt.step()
        if is_main(rank) and step % 5 == 0:
            mon.marker(workload_name, "step", step=step)

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("grad_checkpoint_disguise done steps=%d", steps)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--name", default="grad_checkpoint_disguise")
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
            if w.get("kind") == "grad_checkpoint_disguise":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)

    run(model_cfg, args.steps, args.batch_size, args.seq_len, workload_name=args.name)


if __name__ == "__main__":
    main()
