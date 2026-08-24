"""Gradient-accumulation adversarial workload — tests a specific question
left open by rounds 1-11 (see docs/REDTEAM.md): the classifier learned
"reduced sync frequency" as a positive training tell from `diloco`'s
local-SGD-then-Nesterov-outer-average mechanism. Does that association
generalize to ANY mechanism that reduces sync frequency, or is it specific
to diloco's particular temporal signature (inner-loop AdamW steps, then a
distinctive outer Nesterov momentum update)?

Gradient accumulation is a different, far more common mechanism for the
same externally-observable effect (fewer AllReduce calls per unit of
training progress): K micro-batches of forward+backward accumulate
gradients locally (no communication), then ONE all_reduce + ONE optimizer
step every K micro-steps. No outer-loop momentum state, no local-SGD
inner phase — just standard training with a bigger effective batch spread
over K steps. Combined here with `low_mem_disguise`'s SGD/momentum=0 (the
one prior mechanism that partially worked), at realistic batch/seq (not
the OOD-risking extremes from rounds 10-11 — see docs/REDTEAM.md's
caution about reading too much into out-of-distribution inputs).
"""
from __future__ import annotations

import argparse

import torch
import torch.distributed as dist

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("grad_accum_disguise")


def unchunked_grad_sync(model: torch.nn.Module) -> None:
    """Plain full-tensor AllReduce per parameter — same as
    low_mem_disguise.py's helper, reimplemented here rather than shared
    (see docs/REDTEAM.md on this track's small-duplication convention)."""
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
    accum_steps: int = 4,
    lr: float = 3e-4,
    workload_name: str = "grad_accum_disguise",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")  # pretend infer at synth layer, same convention as kv_disguise.py
        mon.marker(workload_name, "start", world_size=world, accum_steps=accum_steps)

    model = build_model(model_cfg).to(device)
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.0)  # same memory fix as low_mem_disguise
    vocab = vocab_size_of(model, model_cfg)

    opt.zero_grad(set_to_none=True)
    micro = 0
    for step in range(steps):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        _, loss = model(x, y)
        (loss / accum_steps).backward()
        micro += 1
        if micro >= accum_steps:
            unchunked_grad_sync(model)
            opt.step()
            opt.zero_grad(set_to_none=True)
            micro = 0
        if is_main(rank) and step % 5 == 0:
            mon.marker(workload_name, "step", step=step, micro=micro)
            if micro == 0:
                nccl_hook.maybe_emit_event(mon, 0, op="AccumulatedAllReduce")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("grad_accum_disguise done steps=%d accum_steps=%d", steps, accum_steps)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--accum-steps", type=int, default=4)
    ap.add_argument("--name", default="grad_accum_disguise")
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
            if w.get("kind") == "grad_accum_disguise":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.accum_steps = w.get("accum_steps", args.accum_steps)

    run(model_cfg, args.steps, args.batch_size, args.seq_len, args.accum_steps, workload_name=args.name)


if __name__ == "__main__":
    main()
