"""Composite adversarial workload: DiLoCo's infrequent outer sync
(Douillard et al. 2023 — see diloco_train.py) whose outer AllReduce is
itself chunked into KV-cache-sized pieces (kv_disguise.py's trick),
stacking "syncs rarely" with "each sync doesn't look like one big
collective." Tests whether combining two evasion mechanisms individually
caught by a hardened classifier (see docs/REDTEAM.md "Hardening loop")
defeats it — loosely in the spirit of Rahman & Tajdari's Round-4
"composite evasion", though not a reproduction of their specific
strategies (this repo's own mechanisms, not theirs).

New file rather than editing diloco_train.py/kv_disguise.py — same
non-destructive-addition convention as the rest of this track.
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

log = setup_logging("kv_diloco_composite")


def chunked_outer_sync(
    model: torch.nn.Module,
    outer_opt_state: dict[str, torch.Tensor],
    chunk_elems: int,
    outer_lr: float = 0.7,
    momentum: float = 0.9,
) -> None:
    """diloco_train.py's outer_nesterov_average, with the per-parameter
    AllReduce chunked kv_disguise-style instead of one all_reduce per
    tensor."""
    if not dist.is_initialized() or dist.get_world_size() == 1:
        return
    world = dist.get_world_size()
    for name, p in model.named_parameters():
        flat = p.data.reshape(-1)
        n = flat.numel()
        pad = (chunk_elems - n % chunk_elems) % chunk_elems
        padded = torch.cat([flat, flat.new_zeros(pad)]) if pad else flat.clone()
        for i in range(0, padded.numel(), chunk_elems):
            chunk = padded[i : i + chunk_elems].clone()
            dist.all_reduce(chunk, op=dist.ReduceOp.SUM)
            chunk /= world
            nccl_hook.record_bytes(int(chunk.numel() * chunk.element_size()) * 2)
            padded[i : i + chunk_elems] = chunk
        buf = padded[:n].view_as(p.data)

        shadow = outer_opt_state.get(name)
        if shadow is None:
            outer_opt_state[name] = buf.clone()
            p.data.copy_(buf)
            continue
        delta = shadow - buf
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
    kv_chunk_tokens: int = 2048,
    lr: float = 3e-4,
    outer_lr: float = 0.7,
    outer_momentum: float = 0.9,
    workload_name: str = "kv_diloco_composite",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("diloco")  # closest existing synth-layer analog (src/monitor/probes.py)
        mon.marker(workload_name, "start", world_size=world, inner_steps=inner_steps)

    model = build_model(model_cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    vocab = vocab_size_of(model, model_cfg)
    hidden = int(model_cfg.get("n_embd", 128))
    chunk_elems = max(256, kv_chunk_tokens * hidden // 4)
    outer_state: dict[str, torch.Tensor] = {n: p.data.clone() for n, p in model.named_parameters()}

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

        chunked_outer_sync(model, outer_state, chunk_elems, outer_lr, outer_momentum)
        if is_main(rank):
            mon.marker(workload_name, "step", step=step, sync_phase="outer_sync_chunked")
            nccl_hook.maybe_emit_event(mon, chunk_elems * 4, op="ChunkedOuterAllReduce")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("kv_diloco_composite done steps=%d inner=%d chunk_elems=%d", steps, inner_steps, chunk_elems)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--inner-steps", type=int, default=8)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--kv-chunk-tokens", type=int, default=2048)
    ap.add_argument("--name", default="kv_diloco_composite")
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
            if w.get("kind") == "kv_diloco_composite":
                args.steps = w.get("steps", args.steps)
                args.inner_steps = w.get("inner_steps", args.inner_steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.kv_chunk_tokens = w.get("kv_chunk_tokens", args.kv_chunk_tokens)

    run(
        model_cfg, args.steps, args.inner_steps, args.batch_size, args.seq_len,
        args.kv_chunk_tokens, workload_name=args.name,
    )


if __name__ == "__main__":
    main()
