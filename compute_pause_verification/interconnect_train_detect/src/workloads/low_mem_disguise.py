"""Memory-touching adversarial workload — the genuinely new axis flagged in
docs/REDTEAM.md's hardening-loop writeup. Every evasion workload so far
(kv_disguise, diloco, kv_diloco_composite) reshapes COMMUNICATION only —
chunk size, sync frequency — while still using AdamW, whose momentum +
variance state (~8 bytes/param in fp32) is what actually drove
`first_30s_mem_delta_mb`'s separability. This workload instead removes
that memory footprint at the source: plain SGD with momentum=0 has NO
persistent optimizer state (torch's SGD implementation allocates a
momentum buffer only when momentum != 0), so a real backward pass +
optimizer step here should show a much smaller memory ramp than the same
model trained with AdamW — testing whether the classifier's dominant
feature actually generalizes to an optimizer choice that removes the
thing it keys on, rather than just a new communication shape.

`chunk_grad_sync=True` additionally applies kv_disguise's chunked AllReduce
on top, so the loop can isolate memory-only evasion (chunk_grad_sync=False)
from memory+communication combined (chunk_grad_sync=True) as two separate
rounds — change one variable at a time where possible.
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

log = setup_logging("low_mem_disguise")


def chunked_grad_sync(model: torch.nn.Module, chunk_elems: int) -> None:
    """Same chunking idea as kv_disguise.py:kv_shaped_sync, reimplemented
    here rather than imported — see docs/REDTEAM.md on why this track
    prefers small duplication over cross-workload coupling."""
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
    world = dist.get_world_size()
    for i in range(0, flat.numel(), chunk_elems):
        chunk = flat[i : i + chunk_elems].clone()
        dist.all_reduce(chunk, op=dist.ReduceOp.SUM)
        chunk /= world
        nccl_hook.record_bytes(int(chunk.numel() * chunk.element_size()) * 2)
        flat[i : i + chunk_elems] = chunk
    offset = 0
    for p in model.parameters():
        if p.grad is None:
            continue
        numel = p.grad.numel()
        p.grad.copy_(flat[offset : offset + numel].view_as(p.grad))
        offset += numel


def unchunked_grad_sync(model: torch.nn.Module) -> None:
    """Plain full-tensor AllReduce per parameter — isolates the memory
    effect (SGD vs AdamW) from the communication-shape effect."""
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
    chunk_grad_sync: bool = False,
    kv_chunk_tokens: int = 2048,
    lr: float = 3e-4,
    workload_name: str = "low_mem_disguise",
) -> None:
    rank, world, _, device = dist_setup()
    mon = MonitorClient()
    if is_main(rank):
        nccl_hook.reset()
        mon.set_synth_mode("infer")  # pretend infer at synth layer, same convention as kv_disguise.py
        mon.marker(workload_name, "start", world_size=world, chunk_grad_sync=chunk_grad_sync)

    model = build_model(model_cfg).to(device)
    # momentum=0.0 is the whole point: torch.optim.SGD allocates a momentum
    # buffer per parameter only when momentum != 0 (see torch/optim/sgd.py)
    # -- with momentum=0 there is NO persistent optimizer state at all,
    # unlike AdamW's ~8 bytes/param (fp32 momentum + variance).
    opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.0)
    vocab = vocab_size_of(model, model_cfg)
    hidden = int(model_cfg.get("n_embd", 128))
    chunk_elems = max(256, kv_chunk_tokens * hidden // 4)

    for step in range(steps):
        x, y = random_batch(batch_size, seq_len, vocab, device)
        opt.zero_grad(set_to_none=True)
        _, loss = model(x, y)
        loss.backward()
        if chunk_grad_sync:
            chunked_grad_sync(model, chunk_elems)
        else:
            unchunked_grad_sync(model)
        opt.step()
        if is_main(rank) and step % 5 == 0:
            mon.marker(workload_name, "step", step=step, chunk_grad_sync=chunk_grad_sync)
            nccl_hook.maybe_emit_event(mon, 0, op="ChunkedAllReduce" if chunk_grad_sync else "AllReduce")

    if is_main(rank):
        mon.marker(workload_name, "end", steps=steps)
        mon.set_synth_mode("idle")
        log.info("low_mem_disguise done chunk_grad_sync=%s", chunk_grad_sync)
    dist_cleanup()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--steps", type=int, default=40)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--seq-len", type=int, default=64)
    ap.add_argument("--chunk-grad-sync", action="store_true")
    ap.add_argument("--kv-chunk-tokens", type=int, default=2048)
    ap.add_argument("--name", default="low_mem_disguise")
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
            if w.get("kind") == "low_mem_disguise":
                args.steps = w.get("steps", args.steps)
                args.batch_size = w.get("batch_size", args.batch_size)
                args.seq_len = w.get("seq_len", args.seq_len)
                args.chunk_grad_sync = w.get("chunk_grad_sync", args.chunk_grad_sync)
                args.kv_chunk_tokens = w.get("kv_chunk_tokens", args.kv_chunk_tokens)

    run(
        model_cfg, args.steps, args.batch_size, args.seq_len,
        args.chunk_grad_sync, args.kv_chunk_tokens, workload_name=args.name,
    )


if __name__ == "__main__":
    main()
