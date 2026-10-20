"""Cross-check: train on the same pairs with Hugging Face TRL's ``DPOTrainer``.

``dpo.py`` implements DPO by hand so every step is visible. This module runs the reference
implementation on identical inputs, then scores the result with the same evaluation function, so
you can check that the hand-written trainer behaves like the library one.

Identical inputs: each pair is rendered with the same chat template and the same head + tail
prompt truncation that ``dpo.py`` uses, and handed to TRL as plain text (TRL's "standard"
preference format: ``prompt`` / ``chosen`` / ``rejected`` strings). That keeps tokenisation the
same on both sides and sidesteps differences in how libraries handle tool-call messages.

TRL's sigmoid loss is the same formula as ``dpo.dpo_loss``: summed completion log-probs, the
reference given by the base model with the LoRA adapter disabled. Differences in the final
numbers come from batching, data order and optimiser details, not from the objective.

Requires ``pip install trl datasets`` (not part of the core extras).
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from .dpo import encode_pairs, evaluate
from .model import LocalPolicy

log = logging.getLogger(__name__)


def to_text_pairs(policy: LocalPolicy, examples: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Render pairs exactly as dpo.py tokenises them, then decode back to text for TRL."""
    pairs, _ = encode_pairs(policy, examples)
    tok = policy.tokenizer
    return [{"prompt": tok.decode(p.prompt), "chosen": tok.decode(p.chosen), "rejected": tok.decode(p.rejected)}
            for p in pairs]


def train_trl_dpo(policy: LocalPolicy, examples: list[dict[str, Any]], out_dir: Path, *, beta: float,
                  epochs: int, lr: float, grad_accum: int = 4, seed: int = 0) -> dict[str, Any]:
    from datasets import Dataset
    from trl import DPOConfig, DPOTrainer

    out_dir.mkdir(parents=True, exist_ok=True)
    rows = to_text_pairs(policy, examples)
    dataset = Dataset.from_list(rows)
    args = DPOConfig(output_dir=str(out_dir / "trl_out"), per_device_train_batch_size=1,
                     gradient_accumulation_steps=grad_accum, learning_rate=lr, num_train_epochs=epochs,
                     beta=beta, loss_type=["sigmoid"], max_length=None, logging_steps=5, report_to="none",
                     save_strategy="no", seed=seed, gradient_checkpointing=True, bf16=False, fp16=False)
    t0 = time.time()
    trainer = DPOTrainer(model=policy.model, args=args, train_dataset=dataset,
                         processing_class=policy.tokenizer)
    trainer.train()
    log_history = [h for h in trainer.state.log_history if "loss" in h]

    # score with the hand-written evaluation (same reference: adapters disabled)
    pairs, _ = encode_pairs(policy, examples)
    with policy.reference():
        for p in pairs:
            p.ref_chosen = policy.token_logprobs(p.prompt, p.chosen).sum().item()
            p.ref_rejected = policy.token_logprobs(p.prompt, p.rejected).sum().item()
    after = evaluate(policy, pairs, beta)
    summary = {"trainer": "trl.DPOTrainer", "pairs": len(rows), "beta": beta, "epochs": epochs, "lr": lr,
               "after": after, "trl_log": log_history[-3:], "seconds": round(time.time() - t0, 1)}
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary
