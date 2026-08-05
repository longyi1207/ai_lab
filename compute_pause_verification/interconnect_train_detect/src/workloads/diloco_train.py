"""DiLoCo-style low-communication training (Douillard et al. 2023-ish).

Inner AdamW for H steps, then outer Nesterov momentum on parameter delta.
Cross-node traffic ≈ 1/H of DDP — classic Seferis evade.
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

log = setup_logging("diloco")


def outer_nesterov_average(
    model: torch.nn.Module,
    outer_opt_state: dict[str, torch.Tensor],
    outer_lr: float = 0.7,
    momentum: float = 0.9,
) -> None:
    """Average params across ranks, then Nesterov outer step vs local copy in state."""
    if not dist.is_initialized() or dist.get_world_size() == 1:
        return
    for name, p in model.named_parameters():
        # all-reduce current params → mean
        buf = p.data.clone()
        dist.all_reduce(buf, op=dist.ReduceOp.SUM)
        buf /= dist.get_world_size()
        nccl_hook.record_bytes(int(buf.numel() * buf.element_size()) * 2)

        # delta = averaged - previous outer shadow
        shadow = outer_opt_state.get(name)
        if shadow is None:
            outer_opt_state[name] = buf.clone()
            p.data.copy_(buf)
            continue
        delta = shadow - buf  # outer pseudo-grad (DiLoCo uses theta - avg)
        # Nesterov: v = m*v + delta; theta = theta - lr*(delta + m*v)
        vel_key = name + "::v"
        v = outer_opt_state.get(vel_key, torch.zeros_like(delta))
        v = momentum * v + delta
        outer_opt_state[vel_key] = v
        new_shadow = shadow - outer_lr * (delta + momentum * v)
        outer_opt_state[name] = new_shadow
        p.data.copy_(new_shadow)


def run(
    model_cfg: dict,
    steps: int,
    inner_steps: int,
    batch_size: int,
    seq_len: int,
    lr: float = 3e-4,
    outer_lr: float = 0.7,
    outer_momentum: float = 0.9,
    workload_name: str = "diloco",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("diloco")
        mon.marker(workload_name, "start", world_size=world, inner_steps=inner_steps)

    model = build_model(model_cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    vocab = vocab_size_of(model, model_cfg)
    outer_state: dict[str, torch.Tensor] = {
        n: p.data.clone() for n, p in model.named_parameters()
    }

    step = 0
    while step < steps:
        for _ in range(inner_steps):
            if step >= steps:
                break
            x, y = random_batch(batch_size, seq_len, vocab, device)
            opt.zero_grad(set_to_none=True)
            _, loss = model(x, y)
            loss.backward()
            opt.step()
            step += 1
            if is_main(rank) and step % 5 == 0:
                mon.marker(workload_name, "step", step=step, sync_phase="inner")

        outer_nesterov_average(model, outer_state, outer_lr, outer_momentum)
        if is_main(rank):
            mon.marker(workload_name, "step", step=step, sync_phase="outer_sync")
            nccl_hook.maybe_emit_event(mon, 0, op="OuterAllReduce")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("diloco done steps=%d inner=%d", steps, inner_steps)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--inner-steps", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--name", default="diloco")
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
            if w.get("kind") == "diloco":
                args.steps = w.get("steps", args.steps)
                args.inner_steps = w.get("inner_steps", args.inner_steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)

    run(
        model_cfg, args.steps, args.inner_steps,
        args.batch_size, args.seq_len, args.lr, workload_name=args.name,
    )


if __name__ == "__main__":
    main()
