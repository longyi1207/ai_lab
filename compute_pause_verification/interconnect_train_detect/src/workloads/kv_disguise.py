"""Adversarial: disguise param sync as KV-sized chunked collectives."""
from __future__ import annotations

import argparse

import torch
import torch.distributed as dist

from ..model.build import build_model, vocab_size_of
from ..monitor.client import MonitorClient
from ..monitor import nccl_hook
from ..util import load_config, setup_logging
from .dist_utils import dist_cleanup, dist_setup, is_main, random_batch

log = setup_logging("kv_disguise")


def kv_shaped_sync(model: torch.nn.Module, chunk_elems: int) -> None:
    if not dist.is_initialized() or dist.get_world_size() == 1:
        return
    grads = [p.grad.reshape(-1) for p in model.parameters() if p.grad is not None]
    if not grads:
        return
    flat = torch.cat(grads)
    n = flat.numel()
    pad = (chunk_elems - n % chunk_elems) % chunk_elems
    if pad:
        flat = torch.cat([flat, flat.new_zeros(pad)])
    for i in range(0, flat.numel(), chunk_elems):
        chunk = flat[i : i + chunk_elems].clone()
        dist.all_reduce(chunk, op=dist.ReduceOp.SUM)
        chunk /= dist.get_world_size()
        nccl_hook.record_bytes(int(chunk.numel() * chunk.element_size()) * 2)
        flat[i : i + chunk_elems] = chunk
    offset = 0
    for p in model.parameters():
        if p.grad is None:
            continue
        numel = p.grad.numel()
        p.grad.copy_(flat[offset : offset + numel].view_as(p.grad))
        offset += numel


def run(
    model_cfg: dict,
    steps: int,
    batch_size: int,
    seq_len: int,
    kv_chunk_tokens: int = 2048,
    lr: float = 3e-4,
    workload_name: str = "kv_disguise",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")  # pretend infer at synth layer
        mon.marker(workload_name, "start", world_size=world)

    model = build_model(model_cfg).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr)
    vocab = vocab_size_of(model, model_cfg)
    hidden = int(model_cfg.get("n_embd", 128))
    chunk_elems = max(256, kv_chunk_tokens * hidden // 4)

    for step in range(steps):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        kv_shaped_sync(model, chunk_elems)
        opt.step()
        if is_main(rank) and step % 5 == 0:
            mon.marker(workload_name, "step", step=step, chunk_elems=chunk_elems)
            nccl_hook.maybe_emit_event(mon, chunk_elems * 4, op="ChunkedAllReduce")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("kv_disguise done")
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--kv-chunk-tokens", type=int, default=2048)
    ap.add_argument("--name", default="kv_disguise")
    args = ap.parse_args()

    model_cfg = {
        "backend": "tiny",
        "n_layer": 4, "n_head": 4, "n_embd": 128,
        "vocab_size": 256, "block_size": max(args.seq_len, 64),
    }
    if args.config:
        cfg = load_config(args.config)
        model_cfg = {**model_cfg, **cfg.get("model", {})}

    run(
        model_cfg, args.steps, args.batch_size, args.seq_len,
        args.kv_chunk_tokens, workload_name=args.name,
    )


if __name__ == "__main__":
    main()
