# Experiment spec schema

Source of truth: `src/research_dojo/config/spec.py` (`ExperimentSpec` and
friends, Pydantic v2, `extra="forbid"` everywhere — a typo'd key fails fast
instead of being silently ignored). This doc is a human-readable mirror;
if it drifts from the code, trust the code.

## Top level (`ExperimentSpec`)

| Field | Type | Required | Notes |
|---|---|---|---|
| `experiment_id` | str | yes | Stable across runs; groups runs for `dojo experiment show/compare` |
| `hypothesis` | str | yes | Free text — what you're testing and why |
| `model` | `ModelSpec` | yes | |
| `dataset` | str | yes | Path to a JSONL file, **relative to the CWD `dojo` was invoked from** (project root in the documented quickstart), not to the spec file's own directory |
| `arms` | list[str] | no (default `["baseline"]`) | Must be non-empty |
| `rollouts_per_sample` | int | no (default `1`) | |
| `harness` | `HarnessSpec` | no | |
| `verification` | `VerificationSpec` | no | |
| `budget` | `BudgetSpec` | yes | |
| `alerts` | `AlertsSpec` | no | |
| `supervisor` | `SupervisorSpec` | no | |

## `ModelSpec`

| Field | Type | Default |
|---|---|---|
| `provider` | `"azure_openai" \| "openai"` | `azure_openai` |
| `deployment` | str | **required, no default** |
| `temperature` | float | `0.0` |
| `max_tokens` | int | `512` |

## `HarnessSpec`

| Field | Type | Default |
|---|---|---|
| `kind` | `"batch_chat" \| "agent"` | `batch_chat` |
| `max_steps` | int | `10` (agent harness only) |
| `timeout_seconds` | int | `120` (agent harness bash timeout) |

## `VerificationSpec`

| Field | Type | Default |
|---|---|---|
| `deterministic` | bool | `true` |
| `judge` | `JudgeSpec \| null` | `null` (deterministic-only) |

### `JudgeSpec`

| Field | Type | Required |
|---|---|---|
| `rubric` | str (path to rubric md, relative to CWD) | **yes, no default** |
| `version` | str | **yes, no default** — every judgment is stamped with this so a rubric edit is traceable |

## `BudgetSpec` — safety-critical, no silent defaults

| Field | Type | Required |
|---|---|---|
| `max_usd` | float | **yes, no default** — the engine will not run without an explicit cap |
| `max_samples` | int or null | no — caps how many dataset rows are used |

Enforcement: `alerts/rules.py:budget_threshold` fires `budget_threshold`
(warning) at 80% of `max_usd` and `budget_exceeded` (critical, auto-stops the
run -> `BUDGET_STOP`) at 100%, checked after every rollout.

## `AlertsSpec`

| Field | Type | Default |
|---|---|---|
| `webhook_url` | str | `""` (no webhook notifier registered) |
| `"on"` | list[str] | `[]` |

**Gotcha**: YAML 1.1 parses a bare `on:` key as the boolean `True`, not the
string `"on"` (PyYAML's `safe_load` follows the 1.1 spec). Always quote it:
`"on": [run_failed, ...]`. Both shipped specs (`specs/tom_smoke.yaml`,
`tests/fixtures/mini_spec.yaml`) do this — copy that pattern, not a bare `on:`.

`on` is currently descriptive metadata (which rules this run cares about);
the rule evaluators in `alerts/rules.py` run unconditionally and
`alerts/dispatcher.py` filters by `DOJO_ALERT_MIN_SEVERITY`, not by this list.

## `SupervisorSpec`

| Field | Type | Default |
|---|---|---|
| `enabled` | bool | `true` |
| `stale_after_seconds` | int | `600` |

This value is stashed into the frozen spec and read per-run by
`supervisor/daemon.py:_stale_threshold_for` — different runs can have
different staleness tolerances under one supervisor process.

## Environment variable expansion

`${VAR}` and `${VAR:-default}` are expanded against `os.environ` before
Pydantic validation (`config/spec.py:_expand_env`). Load `.env` first (the
CLI does this automatically via `config/settings.load_repo_env()`) or the
substitution will use the fallback / empty string.

## Frozen spec

`ExperimentSpec.freeze()` returns the full validated dict plus a
`spec_hash` (first 16 hex chars of a SHA-256 over the sorted-key JSON dump)
and, when created via the run engine, a `_spec_path` key (not a real spec
field — internal bookkeeping so the supervisor can auto-resume this run
without the caller remembering which file it came from). This frozen dict is
what's stored in `runs.spec_frozen_json` and written to
`artifacts/<run_id>/spec_frozen.json` — it is what `dojo lineage` and
`dojo bundle export` read, not the original YAML file (which may have
changed on disk since).
