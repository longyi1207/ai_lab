"""Dataclass configs for model + training. Deliberately not YAML/Hydra yet — Phase 1 config
surface is small enough that dataclasses + argparse overrides are more legible. Revisit if
Phase 2+ config sweep needs grow past what argparse comfortably expresses.
"""

from dataclasses import dataclass


@dataclass
class ModelConfig:
    vocab_size: int = 50257
    block_size: int = 256       # max sequence length
    n_layer: int = 6
    n_head: int = 6
    n_embd: int = 384
    dropout: float = 0.1
    bias: bool = False          # GPT-2 uses bias in Linear/LayerNorm; modern practice drops it


@dataclass
class TrainConfig:
    data_dir: str = "data/shakespeare"
    out_dir: str = "checkpoints/shakespeare_gpt"
    log_dir: str = "logs"

    # optimization
    max_steps: int = 3000
    micro_batch_size: int = 16          # per-step, per-device batch size
    grad_accum_steps: int = 4           # effective batch = micro_batch_size * grad_accum_steps * world_size
    learning_rate: float = 3e-4
    min_lr: float = 3e-5
    warmup_steps: int = 200
    weight_decay: float = 0.1
    grad_clip: float = 1.0
    beta1: float = 0.9
    beta2: float = 0.95

    # logging / checkpointing
    log_every: int = 20
    eval_every: int = 250
    eval_iters: int = 50            # batches to average for val loss estimate
    checkpoint_every: int = 500
    keep_last_n_checkpoints: int = 3

    # early stopping: stop if val loss hasn't improved for this many consecutive evals.
    # "last N checkpoints" answers "can I resume after a crash"; this answers "which
    # checkpoint should I actually deploy" — two different questions, two mechanisms.
    early_stop_patience: int = 4
    early_stop_min_delta: float = 0.0

    seed: int = 1337
    compile_model: bool = False     # torch.compile — off by default, MPS support is spotty
