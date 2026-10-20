"""Online RL: GRPO with a local policy acting in the environments.

Where DPO trains on pairs collected once, online RL keeps collecting with the *current* policy.
One iteration:

1. pick ``groups_per_iter`` start states: branch points from the pipeline (Docker environments,
   prefix replayed exactly as in stage 4) or the in-process toy task;
2. from each state, roll out K continuations with the current policy, grade them with the task's
   grader, and score them with ``reward.py``; this reuses ``rollout.run_rollout`` unchanged,
   with ``LocalChat`` standing in for the Azure client;
3. compute a **group-relative advantage** per rollout (GRPO, Shao et al. 2024, arXiv:2402.03300):

       A_i = (r_i - mean(r)) / (std(r) + eps)

   If every rollout in a group got the same reward, all its advantages are 0 and it contributes
   no gradient. That is the right behaviour, not a bug: the group says nothing about which choice
   was better;
4. take a gradient step on every token the policy generated. For a generated token t of rollout i:

       ratio_t = exp(logp_new(t) - logp_old(t))
       L_t     = -min(ratio_t * A_i, clip(ratio_t, 1 - eps, 1 + eps) * A_i) + kl_coef * KL_t
       KL_t    = exp(ref_t - new_t) - (ref_t - new_t) - 1        (k3 estimator, always >= 0)

   averaged over the rollout's generated tokens, then over rollouts. Tool outputs and the replayed
   prefix are context only: they are never in the loss. With ``ppo_epochs: 1`` the old and new
   log-probs coincide, so the ratio is 1 and this is REINFORCE with a group-mean baseline plus KL.

The trainer uses the exact token ids the policy generated (recorded by ``LocalChat``), not a
re-rendering of the conversation, so the loss is computed on what was actually sampled.
"""
from __future__ import annotations

import json
import logging
import random
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Any

import torch

from ..rollout import run_rollout
from ..tasks.base import Task
from .model import LocalChat, LocalPolicy

log = logging.getLogger(__name__)

Start = tuple[Task, dict[str, Any] | None, dict[str, Any]]      # (task, recorded episode, branch point)


def group_advantages(rewards: list[float], eps: float = 1e-6) -> list[float]:
    if len(rewards) < 2:
        return [0.0] * len(rewards)
    mean = statistics.fmean(rewards)
    std = statistics.pstdev(rewards)
    if std < 1e-8:
        return [0.0] * len(rewards)
    return [(r - mean) / (std + eps) for r in rewards]


def rollout_group(start: Start, chat: LocalChat, k: int, *, max_new_steps: int, temperature: float,
                  label_source: str, intent_policy: str, tag: str) -> list[dict[str, Any]]:
    """K rollouts from one start state; each record carries the policy's token trace."""
    task, episode, bp = start
    out = []
    for i in range(k):
        chat.trace = []
        rec = run_rollout(task, episode, bp, chat=chat, model=chat.policy.model_name, policy_label=tag,
                          sample_idx=i, max_new_steps=max_new_steps, temperature=temperature,
                          max_tokens=chat.max_new_tokens, label_source=label_source,
                          intent_policy=intent_policy, judge_model=None, phase=tag)
        rec["trace"] = list(chat.trace)
        out.append(rec)
    return out


def grpo_update(policy: LocalPolicy, opt: torch.optim.Optimizer, batch: list[tuple[list[dict], float]], *,
                kl_coef: float, clip_eps: float, ppo_epochs: int) -> dict[str, float]:
    """One or more optimisation passes over (trace, advantage) items."""
    active = [(tr, a) for tr, a in batch if a != 0.0 and any(s["gen_ids"] for s in tr)]
    if not active:
        return {"loss": 0.0, "kl": 0.0, "active_rollouts": 0, "tokens": 0}
    old: dict[tuple[int, int], torch.Tensor] = {}
    ref: dict[tuple[int, int], torch.Tensor] = {}
    with policy.reference():
        for j, (trace, _) in enumerate(active):
            for s, seg in enumerate(trace):
                if seg["gen_ids"]:
                    ref[(j, s)] = policy.token_logprobs(seg["prompt_ids"], seg["gen_ids"])
    stats = {"loss": 0.0, "kl": 0.0, "active_rollouts": len(active),
             "tokens": sum(len(seg["gen_ids"]) for tr, _ in active for seg in tr)}
    policy.model.train()
    for _ in range(ppo_epochs):
        opt.zero_grad()
        total_loss, total_kl = 0.0, 0.0
        for j, (trace, adv) in enumerate(active):
            n_tok = sum(len(seg["gen_ids"]) for seg in trace)
            for s, seg in enumerate(trace):
                if not seg["gen_ids"]:
                    continue
                new = policy.token_logprobs(seg["prompt_ids"], seg["gen_ids"])
                old.setdefault((j, s), new.detach())
                ratio = torch.exp(new - old[(j, s)])
                surrogate = torch.minimum(ratio * adv, torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * adv)
                log_ratio_ref = ref[(j, s)] - new
                kl = torch.exp(log_ratio_ref) - log_ratio_ref - 1
                loss = (-(surrogate - kl_coef * kl)).sum() / n_tok / len(active)
                loss.backward()               # per segment, so long episodes fit in memory
                total_loss += loss.item()
                total_kl += kl.sum().item() / n_tok / len(active)
        grad_norm = torch.nn.utils.clip_grad_norm_(policy.trainable_parameters(), 1.0)
        opt.step()
        # On the first pass the loss is ~0 by construction (ratio = 1 and group advantages have mean
        # 0), so the gradient norm is the number that shows an update actually happened.
        stats["loss"], stats["kl"] = round(total_loss, 5), round(total_kl, 5)
        stats["grad_norm"] = round(float(grad_norm), 4)
    return stats


def _slim(rec: dict[str, Any]) -> dict[str, Any]:
    """Rollout record without bulky fields, for the metrics log."""
    return {k: rec.get(k) for k in ("key", "branch_id", "task", "status", "end", "final_answer", "steps", "verdict")} | {
        "reward": (rec.get("reward") or {}).get("reward"), "reason": (rec.get("reward") or {}).get("reason"),
        "first_turns": [e.get("tool_calls") or e.get("content") for e in (rec.get("entries") or [])
                        if e.get("role") == "assistant"][:3]}


def evaluate_policy(starts: list[Start], chat: LocalChat, n: int, **kw) -> dict[str, Any]:
    recs = []
    for i in range(n):
        recs += rollout_group(starts[i % len(starts)], chat, 1, tag="eval", **kw)
    ok = [r for r in recs if r["status"] == "ok"]
    return {"n": len(ok), "mean_reward": round(statistics.fmean([r["reward"]["reward"] for r in ok]), 3) if ok else None,
            "reasons": dict(Counter(r["reward"]["reason"] for r in ok))}


def train_grpo(policy: LocalPolicy, starts: list[Start], out_dir: Path, *, iterations: int, groups_per_iter: int,
               k: int, lr: float, kl_coef: float, clip_eps: float, ppo_epochs: int, max_new_steps: int,
               temperature: float, max_new_tokens: int, label_source: str, intent_policy: str,
               eval_rollouts: int, seed: int = 0) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(seed)
    chat = LocalChat(policy, max_new_tokens=max_new_tokens)
    opt = torch.optim.AdamW(policy.trainable_parameters(), lr=lr)
    roll_kw = dict(max_new_steps=max_new_steps, temperature=temperature, label_source=label_source,
                   intent_policy=intent_policy)
    metrics, rollouts_log = out_dir / "metrics.jsonl", out_dir / "rollouts.jsonl"
    metrics.write_text("")
    rollouts_log.write_text("")

    before = evaluate_policy(starts, chat, eval_rollouts, **roll_kw) if eval_rollouts else None
    log.info("before training: %s", before)
    t0 = time.time()
    for it in range(1, iterations + 1):
        picked = [starts[rng.randrange(len(starts))] for _ in range(groups_per_iter)]
        batch, rewards_all, reasons, with_signal = [], [], Counter(), 0
        for start in picked:
            recs = rollout_group(start, chat, k, tag=f"grpo_it{it}", **roll_kw)
            ok = [r for r in recs if r["status"] == "ok"]
            rewards = [float(r["reward"]["reward"]) for r in ok]
            adv = group_advantages(rewards)
            with_signal += any(a != 0 for a in adv)
            batch += [(r["trace"], a) for r, a in zip(ok, adv)]
            rewards_all += rewards
            reasons.update(r["reward"]["reason"] for r in ok)
            with rollouts_log.open("a") as f:
                for r, a in zip(ok, adv):
                    f.write(json.dumps(_slim(r) | {"iteration": it, "advantage": round(a, 3)}) + "\n")
        stats = grpo_update(policy, opt, batch, kl_coef=kl_coef, clip_eps=clip_eps, ppo_epochs=ppo_epochs)
        rec = {"iteration": it, "mean_reward": round(statistics.fmean(rewards_all), 3) if rewards_all else None,
               "rollouts": len(rewards_all), "groups_with_signal": with_signal, "reasons": dict(reasons),
               **stats, "seconds": round(time.time() - t0, 1)}
        with metrics.open("a") as f:
            f.write(json.dumps(rec) + "\n")
        log.info("iteration %d: %s", it, rec)

    after = evaluate_policy(starts, chat, eval_rollouts, **roll_kw) if eval_rollouts else None
    log.info("after training: %s", after)
    policy.save_adapter(out_dir / "adapter")
    rows = [json.loads(l) for l in metrics.read_text().splitlines() if l.strip()]
    third = max(1, len(rows) // 3)
    first = [r["mean_reward"] for r in rows[:third] if r["mean_reward"] is not None]
    last = [r["mean_reward"] for r in rows[-third:] if r["mean_reward"] is not None]
    summary = {"model": policy.model_name, "device": policy.device, "iterations": iterations, "k": k,
               "groups_per_iter": groups_per_iter, "lr": lr, "kl_coef": kl_coef, "start_states": len(starts),
               "before": before, "after": after,
               "mean_reward_first_third": round(statistics.fmean(first), 3) if first else None,
               "mean_reward_last_third": round(statistics.fmean(last), 3) if last else None,
               "evaluated_on": "the training start states (proof of concept, not generalisation)",
               "seconds": round(time.time() - t0, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary
