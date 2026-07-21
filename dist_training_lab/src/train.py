"""Phase 1-3 training loop. Launch as:
    .venv/bin/python src/train.py                                        # single process, MPS/CPU
    torchrun --nproc_per_node=4 src/train.py --device cpu                # Phase 2: DDP
    torchrun --nproc_per_node=4 src/train.py --device cpu --parallelism fsdp  # Phase 3: FSDP2

Every design choice below is commented with *why*, not *what* — the *what* is standard
PyTorch. Read README.md for the full rationale (Phase 1/2/3 sections).
"""

import argparse
import json
import math
import time
from contextlib import nullcontext
from pathlib import Path

import torch
import torch.distributed as dist
from torch.distributed.checkpoint.state_dict import (
    StateDictOptions, get_model_state_dict, get_optimizer_state_dict, set_optimizer_state_dict,
)
from torch.distributed.device_mesh import init_device_mesh
from torch.distributed.fsdp import fully_shard
from torch.nn.parallel import DistributedDataParallel as DDP

from config import ModelConfig, TrainConfig
from data import MemmapTokenDataset
from model import GPT, build_optimizer
from utils import (
    DistState, select_device, seed_everything, setup_logging, log_metrics_jsonl,
    save_checkpoint, load_checkpoint, save_best_checkpoint, load_best_meta,
)


def parse_args() -> tuple[ModelConfig, TrainConfig, str, str | None, str]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run_name", type=str, default="shakespeare_gpt")
    # device autodetect (cuda > mps > cpu) is right for Phase 1, but gloo — the CPU-friendly
    # process-group backend used for local multi-process DDP simulation — has no MPS collective
    # support. --device cpu forces the right device for that case; leave unset otherwise.
    parser.add_argument("--device", type=str, default=None, choices=[None, "cpu", "mps", "cuda"])
    # only meaningful when world_size > 1. "ddp" replicates the full model per rank (Phase 2);
    # "fsdp" shards params/grads/optimizer-state per rank (Phase 3, ZeRO-3-equivalent).
    parser.add_argument("--parallelism", type=str, default="ddp", choices=["ddp", "fsdp"])
    # allow overriding any TrainConfig/ModelConfig field from the CLI, e.g. --max_steps 500
    defaults = {**vars(ModelConfig()), **vars(TrainConfig())}
    for key, val in defaults.items():
        parser.add_argument(f"--{key}", type=type(val) if not isinstance(val, bool) else lambda x: x.lower() == "true", default=val)
    args = parser.parse_args()

    model_cfg = ModelConfig(**{k: getattr(args, k) for k in vars(ModelConfig())})
    train_cfg = TrainConfig(**{k: getattr(args, k) for k in vars(TrainConfig())})
    return model_cfg, train_cfg, args.run_name, args.device, args.parallelism


def gather_state_dicts(model: torch.nn.Module, raw_model: torch.nn.Module, optimizer: torch.optim.Optimizer,
                        is_fsdp: bool) -> tuple[dict, dict]:
    """Must be called by EVERY rank when is_fsdp — gathering a full (unsharded) state dict from
    FSDP2's per-rank shards is a collective all-gather, not a local operation. Only rank 0 needs
    the *result* (it's the only one that writes to disk), but every rank must participate in
    producing it or the collective hangs waiting for ranks that never call it. Under DDP/no
    parallelism, this is just a local `.state_dict()` call — no collective, safe to call from
    every rank anyway (keeps the call site uniform instead of branching by mode there too).
    `raw_model` (the un-wrapped reference) is used for the DDP/no-wrap case specifically to
    avoid the "module." key prefix DDP's wrapping would otherwise add.
    """
    if is_fsdp:
        opts = StateDictOptions(full_state_dict=True, cpu_offload=True)
        return get_model_state_dict(model, options=opts), get_optimizer_state_dict(model, optimizer, options=opts)
    return raw_model.state_dict(), optimizer.state_dict()


def get_lr(step: int, cfg: TrainConfig) -> float:
    """Linear warmup then cosine decay to min_lr — the GPT-3/Chinchilla-standard schedule.
    Warmup matters early in training when Adam's second-moment estimate is still noisy;
    without it, large early updates can destabilize training (see GPT-3 paper App. B)."""
    if step < cfg.warmup_steps:
        return cfg.learning_rate * (step + 1) / cfg.warmup_steps
    if step >= cfg.max_steps:
        return cfg.min_lr
    decay_ratio = (step - cfg.warmup_steps) / max(1, cfg.max_steps - cfg.warmup_steps)
    coeff = 0.5 * (1.0 + math.cos(math.pi * decay_ratio))
    return cfg.min_lr + coeff * (cfg.learning_rate - cfg.min_lr)


@torch.no_grad()
def estimate_loss(model: torch.nn.Module, datasets: dict, cfg: TrainConfig, device, dtype, generator) -> dict:
    model.eval()
    out = {}
    for split, ds in datasets.items():
        losses = torch.zeros(cfg.eval_iters)
        for k in range(cfg.eval_iters):
            x, y = ds.get_batch(cfg.micro_batch_size, device, generator)
            with torch.autocast(device_type=device.type, dtype=dtype, enabled=(dtype != torch.float32)):
                _, loss = model(x, y)
            losses[k] = loss.item()
        out[split] = losses.mean().item()
    model.train()
    return out


def main() -> None:
    model_cfg, train_cfg, run_name, device_override, parallelism = parse_args()

    dist_state = DistState()
    dist_state.init_process_group()
    is_fsdp = dist_state.is_ddp and parallelism == "fsdp"  # only meaningful for world_size > 1
    device = select_device(dist_state, override=device_override)
    generator = seed_everything(train_cfg.seed, dist_state.rank)
    logger, jsonl_path = setup_logging(train_cfg.log_dir, run_name, dist_state.is_master)

    if dist_state.is_master:
        logger.info("device=%s world_size=%d parallelism=%s model_cfg=%s",
                     device, dist_state.world_size, parallelism if dist_state.is_ddp else "none", model_cfg)

    # bf16 autocast: no GradScaler needed (unlike fp16) because bf16 has fp32's exponent range,
    # just less mantissa precision — gradients don't underflow the way they can in fp16. CUDA
    # and recent MPS both support bf16 autocast; CPU fallback uses fp32 (autocast disabled).
    if device.type == "cuda" and torch.cuda.is_bf16_supported():
        amp_dtype = torch.bfloat16
    elif device.type == "mps":
        amp_dtype = torch.bfloat16
    else:
        amp_dtype = torch.float32

    meta_path = Path(train_cfg.data_dir) / "meta.json"
    with open(meta_path) as f:
        meta = json.load(f)
    model_cfg.vocab_size = meta["vocab_size"]

    train_ds = MemmapTokenDataset(Path(train_cfg.data_dir) / "train.bin", model_cfg.block_size)
    val_ds = MemmapTokenDataset(Path(train_cfg.data_dir) / "val.bin", model_cfg.block_size)

    model = GPT(model_cfg).to(device)

    resume_ckpt = load_checkpoint(train_cfg.out_dir, device)
    start_step = 0
    if resume_ckpt is not None:
        model.load_state_dict(resume_ckpt["model_state_dict"])
        start_step = resume_ckpt["step"] + 1
        if dist_state.is_master:
            logger.info("Resumed from step %d (%s)", resume_ckpt["step"], train_cfg.out_dir)

    # best-checkpoint / early-stop state. patience_counter intentionally does NOT persist
    # across a resume (simplification) — best_val_loss does, via best_meta.json, so a resumed
    # run still won't overwrite a genuinely better earlier checkpoint with a worse one.
    best_meta = load_best_meta(train_cfg.out_dir)
    best_val_loss = best_meta["val_loss"] if best_meta else float("inf")
    best_step = best_meta["step"] if best_meta else -1
    patience_counter = 0

    raw_model = model
    if dist_state.is_ddp:
        if is_fsdp:
            # per-block sharding: each transformer Block becomes its own FSDP unit, so only one
            # block's parameters are materialized (all-gathered) at a time during forward/backward
            # instead of the whole model at once — this is where FSDP's memory savings actually
            # come from. Wrapping the whole model as a single unit (skip the per-block loop) would
            # still shard storage but lose that "materialize one block at a time" benefit.
            # FSDP2's fully_shard mutates in place and returns the same object — unlike DDP, no
            # separate wrapped reference is created, so `model` and `raw_model` stay the same object.
            #
            # explicit mesh, not autodetected: fully_shard()'s default mesh builder probes for
            # "the current accelerator" and picks MPS just because it's *available* on this
            # machine, regardless of which backend/device we actually initialized (gloo/cpu here)
            # — and torch.mps doesn't implement the is_initialized() check that probe expects,
            # so it crashes. Passing an explicit CPU mesh sidesteps the autodetection entirely.
            mesh = init_device_mesh(device.type, (dist_state.world_size,))
            for block in model.blocks:
                fully_shard(block, mesh=mesh)
            fully_shard(model, mesh=mesh)
        else:
            ddp_backend_device_ids = [dist_state.local_rank] if device.type == "cuda" else None
            model = DDP(model, device_ids=ddp_backend_device_ids)

    if train_cfg.compile_model:
        model = torch.compile(model)

    # built from model.named_parameters() *after* wrapping — required for FSDP correctness (see
    # build_optimizer's docstring), harmless-but-consistent for DDP/no-wrap.
    optimizer = build_optimizer(model.named_parameters(), train_cfg.weight_decay, train_cfg.learning_rate, (train_cfg.beta1, train_cfg.beta2))
    if resume_ckpt is not None:
        if is_fsdp:
            set_optimizer_state_dict(model, optimizer, optim_state_dict=resume_ckpt["optimizer_state_dict"],
                                      options=StateDictOptions(full_state_dict=True, cpu_offload=True))
        else:
            optimizer.load_state_dict(resume_ckpt["optimizer_state_dict"])

    model.train()
    t_last_log = time.time()
    tokens_per_step = train_cfg.micro_batch_size * model_cfg.block_size * train_cfg.grad_accum_steps * dist_state.world_size

    for step in range(start_step, train_cfg.max_steps):
        lr = get_lr(step, train_cfg)
        for group in optimizer.param_groups:
            group["lr"] = lr

        optimizer.zero_grad(set_to_none=True)
        accum_loss = 0.0
        for micro_step in range(train_cfg.grad_accum_steps):
            x, y = train_ds.get_batch(train_cfg.micro_batch_size, device, generator)
            is_last_microstep = micro_step == train_cfg.grad_accum_steps - 1

            # only sync gradients on the final micro-step of accumulation — the default behavior
            # is to sync every backward(), which wastes communication on micro-steps whose
            # gradients we're about to add to anyway. DDP exposes this as a no_sync() context
            # manager; FSDP2 exposes the equivalent as a stateful toggle on the module instead
            # (set_requires_gradient_sync) rather than a context manager — different API, same idea.
            if is_fsdp:
                model.set_requires_gradient_sync(is_last_microstep)
                sync_context = nullcontext()
            else:
                sync_context = model.no_sync() if (dist_state.is_ddp and not is_last_microstep) else nullcontext()
            with sync_context:
                with torch.autocast(device_type=device.type, dtype=amp_dtype, enabled=(amp_dtype != torch.float32)):
                    _, loss = model(x, y)
                    loss = loss / train_cfg.grad_accum_steps
                loss.backward()
            accum_loss += loss.item()

        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), train_cfg.grad_clip)
        optimizer.step()

        if dist_state.is_master and (step % train_cfg.log_every == 0 or step == train_cfg.max_steps - 1):
            now = time.time()
            dt = now - t_last_log
            t_last_log = now
            toks_per_sec = (tokens_per_step * train_cfg.log_every) / dt if step > start_step else tokens_per_step / dt
            mem_gb = torch.mps.current_allocated_memory() / 1e9 if device.type == "mps" else (
                torch.cuda.max_memory_allocated() / 1e9 if device.type == "cuda" else 0.0)
            logger.info(
                "step %5d | loss %.4f | lr %.2e | grad_norm %.3f | tok/s %.0f | mem %.2fGB",
                step, accum_loss, lr, grad_norm.item(), toks_per_sec, mem_gb,
            )
            log_metrics_jsonl(jsonl_path, {
                "step": step, "train_loss": accum_loss, "lr": lr,
                "grad_norm": grad_norm.item(), "tokens_per_sec": toks_per_sec, "mem_gb": mem_gb,
            })

        do_early_stop = torch.zeros(1, dtype=torch.uint8, device=device)
        if step > start_step and step % train_cfg.eval_every == 0:
            # forward pass is itself a collective under FSDP (each block's all-gather needs
            # every rank), so estimate_loss must run on every rank here, not just master — unlike
            # Phase 1/2 where forward had no collectives and this could safely be master-only.
            losses = estimate_loss(model, {"train": train_ds, "val": val_ds}, train_cfg, device, amp_dtype, generator)
            # gathering a full state dict under FSDP is also collective — every rank must call
            # this even though only master ends up writing to disk. Simplification: this gathers
            # every eval step regardless of whether it turns out to be a new best, which is
            # wasteful at real scale (full-model all-gather just to maybe throw it away) — fine
            # at 30M params, not how you'd do this at 100B+ (see README Phase 3 log).
            model_sd, optim_sd = gather_state_dicts(model, raw_model, optimizer, is_fsdp)

            if dist_state.is_master:
                logger.info("step %5d | eval train_loss %.4f val_loss %.4f", step, losses["train"], losses["val"])
                log_metrics_jsonl(jsonl_path, {"step": step, "eval_train_loss": losses["train"], "eval_val_loss": losses["val"]})

                if losses["val"] < best_val_loss - train_cfg.early_stop_min_delta:
                    best_val_loss, best_step = losses["val"], step
                    patience_counter = 0
                    best_path = save_best_checkpoint(train_cfg.out_dir, step, losses["val"], model_sd, optim_sd, model_cfg, train_cfg)
                    logger.info("New best val_loss %.4f at step %d -> %s", losses["val"], step, best_path)
                else:
                    patience_counter += 1
                    logger.info("No improvement (%d/%d since best): best val_loss %.4f at step %d",
                                 patience_counter, train_cfg.early_stop_patience, best_val_loss, best_step)
                    if patience_counter >= train_cfg.early_stop_patience:
                        logger.info("Early stopping at step %d — val_loss hasn't improved in %d evals (best: %.4f @ step %d).",
                                     step, train_cfg.early_stop_patience, best_val_loss, best_step)
                        do_early_stop[0] = 1

        # every rank must agree to stop together, or non-master ranks would hang waiting on
        # a collective (e.g. the next DDP all-reduce, or any FSDP forward pass) that master
        # never issues after breaking.
        if dist_state.is_ddp:
            dist.broadcast(do_early_stop, src=0)

        if step > start_step and step % train_cfg.checkpoint_every == 0:
            model_sd, optim_sd = gather_state_dicts(model, raw_model, optimizer, is_fsdp)  # all ranks
            if dist_state.is_master:
                ckpt_path = save_checkpoint(train_cfg.out_dir, step, model_sd, optim_sd, model_cfg, train_cfg, train_cfg.keep_last_n_checkpoints)
                logger.info("Saved checkpoint: %s", ckpt_path)

        dist_state.barrier()

        if do_early_stop.item():
            break

    model_sd, optim_sd = gather_state_dicts(model, raw_model, optimizer, is_fsdp)  # all ranks
    if dist_state.is_master:
        final_ckpt = save_checkpoint(train_cfg.out_dir, step, model_sd, optim_sd, model_cfg, train_cfg, train_cfg.keep_last_n_checkpoints)
        logger.info("Training complete at step %d. Final checkpoint: %s. Best: val_loss %.4f @ step %d (checkpoints/.../best.pt).",
                     step, final_ckpt, best_val_loss, best_step)

    dist_state.destroy()


if __name__ == "__main__":
    main()
