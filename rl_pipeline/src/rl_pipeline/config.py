"""Load and validate the pipeline configuration (one YAML file per run).

Every knob the pipeline uses lives in the config, so a run is reproducible from its config file
plus the recorded episodes. Two conveniences keep personal details out of the committed YAML:

* ``${VAR}`` and ``${VAR:-default}`` are expanded from the environment (after ``azure.env_file``
  is loaded), so resource names and local paths can come from your shell or ``.env``.
* Relative paths are resolved against the directory that contains the config file.

Unknown keys are an error: a typo such as ``max_pair_per_branch`` should fail loudly, not be
silently ignored.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


@dataclass
class PathsConfig:
    score_seeking_eval: Path = Path("../score-seeking-eval")
    runs_dir: Path | None = None          # default: <score_seeking_eval>/runs
    output_dir: Path = Path("outputs")


@dataclass
class AzureConfig:
    env_file: Path | None = None
    policy_deployment: str = "gpt-4.1-mini"
    judge_deployment: str = "gpt-5.4"
    finetune_base_model: str = "gpt-4.1-mini-2025-04-14"
    training_type: str = "GlobalStandard"
    # Only needed to create and delete the fine-tuned deployment (through the `az` CLI).
    subscription_id: str | None = None
    resource_group: str | None = None
    account_name: str | None = None


@dataclass
class SelectConfig:
    tasks: list[str] = field(default_factory=lambda: ["internal_exfil", "protocol_re"])
    max_branch_points_per_task: int = 40
    margin: int = 1
    include_temptation_points: bool = True
    test_fraction: float = 0.25
    seed: int = 0


@dataclass
class SampleConfig:
    k: int = 4
    temperature: float = 1.0
    max_new_steps: int = 60       # capped per task at the runner's own step budget
    max_tokens: int = 2048
    workers: int = 6


@dataclass
class RewardConfig:
    # "outcome_action": preference labels come from the grader only (completion + behaviour).
    # "full": also require a clean intent judgement (puts optimisation pressure on reasoning).
    label_source: str = "outcome_action"
    intent_policy: str = "pursuit"


@dataclass
class JudgeConfig:
    enabled: bool = True
    scope: str = "eval"                   # "eval" (evaluation rollouts only) or "all"


@dataclass
class PairsConfig:
    max_pairs_per_branch: int = 4
    val_fraction: float = 0.1
    min_pairs: int = 10
    # Also use the recorded episode's own continuation as a graded sample from the branch state.
    include_recorded: bool = False


@dataclass
class FinetuneConfig:
    beta: float | None = 0.1
    n_epochs: int | None = 2
    suffix: str = "rlp"
    deployment_name: str = "rlp-tuned"
    deployment_sku: str = "DeveloperTier"
    deployment_capacity: int = 50
    poll_seconds: int = 60


@dataclass
class EvaluateConfig:
    k: int = 4
    fresh_episodes: int = 0               # full episodes from step 0, per (task, policy); 0 = off


@dataclass
class LocalConfig:
    """Self-hosted training (``rl_pipeline.local``): a small open-weight model with LoRA."""
    model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    device: str = "auto"                  # auto = mps, then cuda, then cpu
    lora_r: int = 16
    lora_alpha: int = 32
    max_prompt_tokens: int = 2048         # head + tail truncation of long contexts
    max_new_tokens: int = 256
    temperature: float = 1.0
    seed: int = 0
    # offline DPO
    dpo_beta: float = 0.1
    dpo_epochs: int = 3
    dpo_lr: float = 1e-4
    dpo_max_pairs: int = 0                # 0 = all pairs
    # online GRPO
    grpo_env: str = "toy"                 # "toy" (in-process) or "branch" (Docker branch points)
    grpo_iterations: int = 20
    grpo_groups_per_iter: int = 2
    grpo_k: int = 6
    grpo_lr: float = 2e-5
    grpo_kl_coef: float = 0.04
    grpo_clip_eps: float = 0.2
    grpo_ppo_epochs: int = 1
    grpo_max_new_steps: int = 4
    grpo_branch_points: int = 4           # how many branch points to train on when grpo_env=branch
    grpo_eval_rollouts: int = 12


@dataclass
class BudgetConfig:
    max_usd: float = 45.0
    # USD per 1M tokens. Keys are matched against the deployment/model name by longest prefix.
    prices: dict[str, dict[str, float]] = field(default_factory=dict)
    training_usd_per_mtok: float = 5.0


@dataclass
class Config:
    run_name: str = "pilot"
    paths: PathsConfig = field(default_factory=PathsConfig)
    azure: AzureConfig = field(default_factory=AzureConfig)
    select: SelectConfig = field(default_factory=SelectConfig)
    sample: SampleConfig = field(default_factory=SampleConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    judge: JudgeConfig = field(default_factory=JudgeConfig)
    pairs: PairsConfig = field(default_factory=PairsConfig)
    finetune: FinetuneConfig = field(default_factory=FinetuneConfig)
    evaluate: EvaluateConfig = field(default_factory=EvaluateConfig)
    local: LocalConfig = field(default_factory=LocalConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    source_path: Path | None = None

    @property
    def runs_dir(self) -> Path:
        return self.paths.runs_dir or (self.paths.score_seeking_eval / "runs")

    @property
    def run_dir(self) -> Path:
        return self.paths.output_dir / self.run_name


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        return _VAR.sub(lambda m: os.environ.get(m.group(1)) or (m.group(2) or ""), value)
    if isinstance(value, list):
        return [_expand(v) for v in value]
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    return value


def _build(cls: type, data: dict[str, Any], where: str) -> Any:
    known = {f.name: f for f in fields(cls)}
    unknown = sorted(set(data) - set(known))
    if unknown:
        raise ValueError(f"unknown config key(s) in {where}: {unknown}")
    kwargs = {}
    for name, value in data.items():
        default = getattr(cls(), name)
        if is_dataclass(default) and isinstance(value, dict):
            kwargs[name] = _build(type(default), value, f"{where}.{name}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


def _resolve(base: Path, value: Any) -> Path | None:
    if value in (None, ""):
        return None
    p = Path(value).expanduser()
    return p if p.is_absolute() else (base / p).resolve()


def load_config(path: str | Path, *, env_file: str | Path | None = None) -> Config:
    """Read a YAML config, load its env file, expand ${VARS}, and resolve paths.

    ``env_file`` (or the ``RL_PIPELINE_ENV_FILE`` environment variable) overrides
    ``azure.env_file`` from the YAML. Keys already in the environment are never overwritten.
    """
    path = Path(path).resolve()
    base = path.parent
    raw = yaml.safe_load(path.read_text()) or {}

    env_override = env_file or os.environ.get("RL_PIPELINE_ENV_FILE")
    yaml_env = (raw.get("azure") or {}).get("env_file")
    env_path = _resolve(Path.cwd(), env_override) if env_override else _resolve(base, _expand(yaml_env))
    if env_path is not None:
        if not env_path.is_file():
            raise FileNotFoundError(f"env file not found: {env_path}")
        load_dotenv(env_path, override=False)

    cfg: Config = _build(Config, _expand(raw), "config")
    cfg.source_path = path
    cfg.azure.env_file = env_path
    cfg.paths.score_seeking_eval = _resolve(base, cfg.paths.score_seeking_eval)
    cfg.paths.runs_dir = _resolve(base, cfg.paths.runs_dir)
    cfg.paths.output_dir = _resolve(base, cfg.paths.output_dir)

    if cfg.reward.label_source not in ("outcome_action", "full"):
        raise ValueError("reward.label_source must be 'outcome_action' or 'full'")
    if cfg.judge.scope not in ("eval", "all"):
        raise ValueError("judge.scope must be 'eval' or 'all'")
    if cfg.reward.label_source == "full" and not (cfg.judge.enabled and cfg.judge.scope == "all"):
        raise ValueError("label_source 'full' needs the intent judge on every rollout (judge.scope: all)")
    return cfg
