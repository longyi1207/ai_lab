# Pipeline reference

Stage by stage: what each one reads, what it writes, what it costs, and how it fails. For *why*
each stage exists, see [concepts.md](concepts.md).

All commands run from the `rl_pipeline/` directory:

```bash
python -m rl_pipeline <stage> --config configs/pilot.yaml [--limit N]
```

Outputs go to `outputs/<run_name>/` (git-ignored: they contain full transcripts, including
working shortcut commands against the toy environments).

## Stages

| # | stage | reads | writes | calls a model? |
|---|---|---|---|---|
| 1 | `import` | `<runs_dir>/**/*.json` | `episodes.jsonl`, `import_summary.json` | no |
| 2 | `select` | `episodes.jsonl` | `branch_points.jsonl`, `select_summary.json` | no |
| 3 | `replay` | branch points + episodes | `replay_check.jsonl` | no (Docker only) |
| 4 | `sample` | train branch points that replay | `rollouts.jsonl` (`phase: sample`) | policy |
| 5 | `pairs` | sample rollouts | `pairs/train.jsonl`, `pairs/val.jsonl`, `pairs/meta.jsonl` | no |
| 6 | `finetune` | pairs | `finetune/state.json` | fine-tuning job |
| 6b | `deploy` | fine-tuned model id | a Developer-tier deployment | no (az CLI) |
| 7 | `evaluate` | test branch points | `rollouts.jsonl` (`phase: eval`), `eval/summary.json` | base, tuned, judge |
| 7b | `teardown` | deployment name | deletes the deployment | no |
| 8 | `report` | everything above | `REPORT.md` | no |

`run-all` runs 1 through 8 in order and tears the deployment down before writing the report.

### 1. import

Reads every run JSON under `runs_dir`, keeps runs of the configured tasks that have a transcript
and a grader label, in conditions the task supports (for example `protocol_re` with
`salient=off` has no flag objective, so it is skipped). Identical transcripts are kept once.
Each episode is scored with [`reward.py`](../src/rl_pipeline/reward.py).

### 2. select

For each episode, finds the onset step from the intent judge's evidence quotes and branches
`margin` steps before it. Two kinds of source episode are used: `pursued` (the agent went for the
shortcut) and `temptation` (it noticed the shortcut and declined). Selection is round-robin over
(source model, kind) so no single model dominates, capped at `max_branch_points_per_task`. The
train/test split hashes the source episode id.

Reasons an episode is not used are counted in `select_summary.json`: no decision to branch from,
onset not located, onset too early (we need at least one recorded step of context), over the cap.

### 3. replay

Starts a fresh container per branch point, re-runs the recorded commands, and compares outputs
after masking (`replay.normalize_output`). Only branch points marked `ok` are sampled from.
Mismatches are stored (first ten, two thousand characters each) for debugging.

### 4. sample

For each training branch point that replays, K continuations from `azure.policy_deployment` at
`sample.temperature`. Each rollout replays the prefix in its own container (memory state such as a
device's authentication phase cannot be snapshotted with `docker commit`), runs the agent loop for
at most `max_new_steps`, grades, and scores. One JSON line per rollout, keyed
`<branch_id>|<policy>|<sample_idx>`; reruns skip finished keys.

Rollout statuses: `ok`, `replay_mismatch`, `provider_error:<kind>` (for example a content-filter
refusal), `sandbox_error`, `error:<Exception>`. Only `ok` rollouts become training data.

### 5. pairs

Pairs every reward-1 continuation with every reward-0 continuation at the same branch point (up to
`max_pairs_per_branch`, sampled with a fixed seed), places the preference on the first divergent
turn, validates each example's structure, and splits by branch point into train and validation.
`pairs/summary.json` reports how many branch points had contrast at all.

Example line (abridged):

```json
{"input": {"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."},
                        {"role": "assistant", "tool_calls": [...]}, {"role": "tool", "content": "..."}],
           "tools": [...], "parallel_tool_calls": true},
 "preferred_output": [{"role": "assistant", "tool_calls": [{"function": {"name": "bash", "arguments": "..."}}]}],
 "non_preferred_output": [{"role": "assistant", "tool_calls": [...]}]}
```

### 6. finetune, deploy

Uploads the pair files, submits a job with `method={"type": "dpo"}` and
`trainingType: GlobalStandard`, polls it, and records the fine-tuned model id. Before submitting,
the training cost is estimated (characters / 4 x epochs x `training_usd_per_mtok`) and checked
against the budget. `deploy` creates a Developer-tier deployment with the `az` CLI, which needs
`azure.resource_group` and `azure.account_name` and an `az login`. A new deployment answers 400
(`BadRequestForDependentService`) for a few minutes; `deploy` polls it until a test call succeeds.
Developer-tier capacity is at most 250 (thousand tokens per minute), so evaluation of the tuned
model is slower than sampling from the base. Developer-tier deployments are deleted by Azure after
24 hours; `teardown` deletes it sooner.

The job's metrics file (`finetune/results.csv`: training loss and error rate per step, validation
metrics every 10 steps) is worth reading before trusting the evaluation.

### 7. evaluate

Both policies continue from every test branch point (`evaluate.k` samples each), plus
`fresh_episodes` full episodes per task from step 0. The intent judge runs on all of them.
`eval/summary.json` holds rates with Wilson intervals and the paired per-branch-point delta.

## Configuration

Every key with its default is in [`config.py`](../src/rl_pipeline/config.py). The ones you are most
likely to change:

| key | meaning |
|---|---|
| `paths.score_seeking_eval` | local checkout providing task code, graders and prompts |
| `paths.runs_dir` | recorded episodes (default `<score_seeking_eval>/runs`) |
| `azure.policy_deployment` | the deployment you sample from; should be the base of `finetune_base_model` so the data is on-policy |
| `select.margin` | how many steps before the onset to branch |
| `sample.k` | continuations per branch point; more samples, more branch points with contrast |
| `reward.label_source` | `outcome_action` (grader only) or `full` (also intent) |
| `pairs.include_recorded` | also use the recorded episode's own continuation as a graded sample from the branch state |
| `budget.max_usd` | hard cap across the whole run, including restarts |
| `local.*` | self-hosted DPO/GRPO settings, see [local_training.md](local_training.md) |

Any key can be overridden for one run: `--set sample.k=8 --set local.grpo_iterations=2`.

## Budget and resuming

Every billed call is appended to `spend.jsonl`. The budget reads it on start-up, so the cap covers
the run across restarts. When the cap is reached the current stage stops, finished rollouts stay
on disk, and the CLI exits with status 2. Raise `budget.max_usd` and rerun the stage to continue.

## Adding a task

Write a `Task` subclass in `src/rl_pipeline/tasks/` that provides the Docker image, tools, system
and user prompts (ideally read from the original runner so rebuilt conversations match), the
runner's nudge text, `prepare` (wait for services, plant files), and `grade` (call the task's own
grader). Register it in `tasks/__init__.py`, and add any new grader signal names to
`reward.TAMPER_SIGNALS`.

## Known limitations

* Recorded prefixes come from other models (DeepSeek, Kimi, GPT-4o, GPT-5.4); only the
  continuations are sampled from the policy being trained.
* When two containers issue different random tokens, the two sides of a pair can have slightly
  different contexts. The pair uses the preferred side's context; `pairs/meta.jsonl` marks which
  pairs are byte-identical.
* The agent's private reasoning from the recorded models is not sent back to the policy (chat APIs
  do not accept another model's reasoning as input), so the policy sees its "earlier self" only
  through visible messages and tool calls.
