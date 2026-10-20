"""Offline training: DPO from scratch on the pipeline's preference pairs.

This trains on exactly the file the Azure job uses (``pairs/train.jsonl``), so you can read the
algorithm end to end instead of trusting a hosted API.

**The DPO objective** (Rafailov et al. 2023, arXiv:2305.18290). For a prompt x with a preferred
completion y_w and a rejected completion y_l:

    log-ratio of a completion   r(y) = log pi_theta(y | x) - log pi_ref(y | x)
    loss                        L    = -log sigmoid( beta * (r(y_w) - r(y_l)) )

``log pi(y | x)`` is the sum of the per-token log-probabilities of the completion. ``r(y)`` is the
"implicit reward": how much more likely the trained policy makes y than the frozen reference
does. The loss pushes the preferred completion's implicit reward above the rejected one's.
``beta`` sets how far the policy may move from the reference; smaller beta allows larger moves.

Reference log-probs never change, so they are computed once before training. Metrics logged
every step: loss, reward accuracy (fraction of pairs with r(y_w) > r(y_l)), and the margin.

This module trains and evaluates on the same pairs (a proof of concept on a laptop, not a
generalisation result): what it shows is that the loss, the gradients and the adapters work.
"""
from __future__ import annotations

import json
import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

from .model import LocalPolicy

log = logging.getLogger(__name__)


@dataclass
class PairTensors:
    prompt: list[int]
    chosen: list[int]
    rejected: list[int]
    ref_chosen: float = 0.0
    ref_rejected: float = 0.0


def encode_pairs(policy: LocalPolicy, examples: list[dict[str, Any]]) -> tuple[list[PairTensors], int]:
    """Azure DPO lines -> token ids. Returns (pairs, number skipped)."""
    out, skipped = [], 0
    for ex in examples:
        ctx, tools = ex["input"]["messages"], ex["input"].get("tools")
        try:
            p, c = policy.encode_pair_side(ctx, ex["preferred_output"][0], tools)
            p2, r = policy.encode_pair_side(ctx, ex["non_preferred_output"][0], tools)
        except ValueError:
            skipped += 1
            continue
        if p != p2 or c == r:
            skipped += 1
            continue
        out.append(PairTensors(p, c, r))
    return out, skipped


def dpo_loss(pi_w: torch.Tensor, pi_l: torch.Tensor, ref_w: float, ref_l: float, beta: float
             ) -> tuple[torch.Tensor, float, float]:
    """(loss, reward accuracy, margin) for one pair, from summed log-probs."""
    margin = beta * ((pi_w - ref_w) - (pi_l - ref_l))
    return -F.logsigmoid(margin), float(margin.item() > 0), float(margin.item())


def evaluate(policy: LocalPolicy, pairs: list[PairTensors], beta: float) -> dict[str, float]:
    """Loss, reward accuracy, margin, and the raw preference over ``pairs`` (no gradients).

    Before training the policy *is* the reference (LoRA adapters start at zero), so every margin
    is exactly 0 and reward accuracy is 0. ``raw_preference`` (the fraction of pairs where the
    policy gives the preferred turn a higher total log-probability) shows where the model starts.
    """
    policy.model.eval()
    losses, accs, margins, raw = [], [], [], []
    with torch.no_grad():
        for p in pairs:
            pi_w = policy.token_logprobs(p.prompt, p.chosen).sum()
            pi_l = policy.token_logprobs(p.prompt, p.rejected).sum()
            loss, acc, m = dpo_loss(pi_w, pi_l, p.ref_chosen, p.ref_rejected, beta)
            losses.append(loss.item()); accs.append(acc); margins.append(m)
            raw.append(float(pi_w.item() > pi_l.item()))
    n = max(1, len(pairs))
    return {"loss": round(sum(losses) / n, 4), "reward_accuracy": round(sum(accs) / n, 3),
            "margin": round(sum(margins) / n, 4), "raw_preference": round(sum(raw) / n, 3)}


def train_dpo(policy: LocalPolicy, examples: list[dict[str, Any]], out_dir: Path, *, beta: float,
              epochs: int, lr: float, grad_accum: int = 4, seed: int = 0) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pairs, skipped = encode_pairs(policy, examples)
    if not pairs:
        raise RuntimeError("no usable pairs")
    log.info("DPO on %d pairs (%d skipped); prompt tokens up to %d", len(pairs), skipped,
             max(len(p.prompt) for p in pairs))

    # 1. reference log-probs, once
    with policy.reference():
        for p in pairs:
            p.ref_chosen = policy.token_logprobs(p.prompt, p.chosen).sum().item()
            p.ref_rejected = policy.token_logprobs(p.prompt, p.rejected).sum().item()

    before = evaluate(policy, pairs, beta)
    log.info("before: %s", before)

    # 2. optimise
    opt = torch.optim.AdamW(policy.trainable_parameters(), lr=lr)
    rng = random.Random(seed)
    metrics_path = out_dir / "metrics.jsonl"
    metrics_path.write_text("")
    step, t0 = 0, time.time()
    for epoch in range(epochs):
        order = list(range(len(pairs)))
        rng.shuffle(order)
        policy.model.train()
        opt.zero_grad()
        for i, idx in enumerate(order):
            p = pairs[idx]
            pi_w = policy.token_logprobs(p.prompt, p.chosen).sum()
            pi_l = policy.token_logprobs(p.prompt, p.rejected).sum()
            loss, acc, margin = dpo_loss(pi_w, pi_l, p.ref_chosen, p.ref_rejected, beta)
            (loss / grad_accum).backward()
            if (i + 1) % grad_accum == 0 or i + 1 == len(order):
                torch.nn.utils.clip_grad_norm_(policy.trainable_parameters(), 1.0)
                opt.step()
                opt.zero_grad()
            step += 1
            rec = {"step": step, "epoch": epoch, "loss": round(loss.item(), 4), "reward_accuracy": acc,
                   "margin": round(margin, 4), "seconds": round(time.time() - t0, 1)}
            with metrics_path.open("a") as f:
                f.write(json.dumps(rec) + "\n")
        log.info("epoch %d done (%.0fs)", epoch + 1, time.time() - t0)

    after = evaluate(policy, pairs, beta)
    log.info("after: %s", after)
    policy.save_adapter(out_dir / "adapter")
    summary = {"model": policy.model_name, "device": policy.device, "pairs": len(pairs), "skipped": skipped,
               "beta": beta, "epochs": epochs, "lr": lr, "before": before, "after": after,
               "evaluated_on": "the training pairs (proof of concept, not generalisation)",
               "seconds": round(time.time() - t0, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
