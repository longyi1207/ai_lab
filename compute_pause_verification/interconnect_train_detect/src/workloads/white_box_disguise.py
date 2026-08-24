"""White-box adversary — combines everything learned so far (see
docs/REDTEAM.md), rather than testing one variable at a time:

- SGD, momentum=0 (low_mem_disguise's memory fix — the one mechanism that
  partially worked)
- realistic batch_size/seq_len (round 8's values, NOT the OOD-risking
  extremes from rounds 10-11 — staying in the region where the
  classifier's judgments actually mean something)
- NO communication-shape changes (chunking/sparse-sync were shown to
  become learned positive "training" tells once caught once — this
  workload deliberately does the plain, unchunked, every-step AllReduce)
- NEW: deliberate idle gaps between steps, sized as a fraction of the
  compute time each step actually took. Nothing tested so far has touched
  the TEMPORAL/duty-cycle features (cv_power, cv_util, periodicity_power,
  periodicity_util) directly — training in this repo so far always grinds
  continuously; real inference serving is bursty (request arrives, GPU
  computes, then waits). This targets that axis specifically, on top of
  the one prior partial win, rather than yet another single-variable
  sweep.
"""
from __future__ import annotations

import argparse
import time

import torch
import torch.distributed as dist

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("white_box_disguise")


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
    idle_frac: float = 1.0,
    lr: float = 3e-4,
    workload_name: str = "white_box_disguise",
) -> None:
    """idle_frac=1.0 means: sleep for as long as the step's compute took
    (i.e. ~50% duty cycle overall) — a bursty, request-shaped rhythm
    rather than continuous grinding. 0 disables idle gaps (still useful as
    an ablation)."""
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")
        mon.marker(workload_name, "start", world_size=world, idle_frac=idle_frac)

    model = build_model(model_cfg).to(device)
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.0)
    vocab = vocab_size_of(model, model_cfg)

    for step in range(steps):
        t0 = time.time()
        x, y = random_batch(batch_size, seq_len, vocab, device)
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        unchunked_grad_sync(model)
        opt.step()
        if device.type == "cuda":
            torch.cuda.synchronize(device)
        compute_s = time.time() - t0

        if idle_frac > 0:
            time.sleep(compute_s * idle_frac)

        if is_main(rank) and step % 5 == 0:
            mon.marker(workload_name, "step", step=step, compute_s=compute_s)

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("white_box_disguise done steps=%d idle_frac=%.2f", steps, idle_frac)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--idle-frac", type=float, default=1.0)
    ap.add_argument("--name", default="white_box_disguise")
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
            if w.get("kind") == "white_box_disguise":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.idle_frac = w.get("idle_frac", args.idle_frac)

    run(model_cfg, args.steps, args.batch_size, args.seq_len, args.idle_frac, workload_name=args.name)


if __name__ == "__main__":
    main()
