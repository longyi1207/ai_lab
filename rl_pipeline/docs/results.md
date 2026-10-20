# Results: the pilot run

What happened when the whole pipeline ran end to end, including what did not work the first time.
Run date 2026-10-20. Config: [`configs/pilot.yaml`](../configs/pilot.yaml).

> **How to read these numbers.** This is a pilot. Sample sizes are small, so every rate comes with
> a Wilson 95% interval. Recorded episodes come from five other models (DeepSeek-V4-Pro,
> Kimi-K2.6, GPT-4o, GPT-5.4, Claude Sonnet 4.5); the policy we sample from and train is
> `gpt-4.1-mini`. The local-training numbers are trained and evaluated on the same data: they
> show the code works, not that the method generalises.

## 1. From recorded runs to training data

| stage | result |
|---|---|
| recorded episodes imported | 358 (internal_exfil 183, protocol_re 175) |
| branch points selected | 80 (40 per task); 64 episodes skipped because no evidence quote could be located, 11 because the onset was too early to branch |
| prefixes that replay faithfully in a fresh container | **78 / 80** (protocol_re 40/40, internal_exfil 38/40) |
| training rollouts (gpt-4.1-mini, K=4) | 228 on 57 training branch points, all completed after retries |
| preference pairs | 88 train / 4 validation, from 23 of the 57 branch points |
| Azure spend for sampling | about $8 |

One of the two replay failures was a real change to the environment since the episode was
recorded (`/app/PROBLEM.md` had been edited); rejecting it is the behaviour we want.

### What the base policy did from the training branch points

| task | took the shortcut | did not finish | finished honestly |
|---|---|---|---|
| internal_exfil | 86 | 19 | 7 |
| protocol_re | 79 | 36 | 1 |

From states where another model had started to notice the shortcut, `gpt-4.1-mini` took it most of
the time and rarely finished the honest path. That has a direct consequence for the method: a
preference pair needs a 1 and a 0 from the same state, and the policy's own samples provided a 1 at
only 7 branch points. The pilot therefore also used each branch point's recorded continuation as a
graded sample (`pairs.include_recorded`, explained in [concepts §5](concepts.md#5-from-continuations-to-preference-pairs)):

| pairs | count |
|---|---|
| preferred side written by the recorded agent / by gpt-4.1-mini | 69 / 23 |
| rejected side: took the shortcut / did not finish | 66 / 26 |
| first divergent turn: 0 / 1 | 90 / 2 |
| both contexts byte-identical (the rest differ only in masked nonces) | 44 / 92 |

Most pairs diverge at the very first continuation turn, because the branch is placed just before
the step where the recorded agent first mentioned the shortcut, and in these tasks that happens
early (the handoff note or config file is read in the first few steps).

## 2. Hosted DPO on Azure OpenAI

**The job.** `gpt-4.1-mini-2025-04-14`, method DPO (beta 0.1, 2 epochs, other hyperparameters at
the service defaults), Global training. 300,446 trained tokens, about $1.50, roughly 45 minutes of
training after queueing. Two earlier tiny jobs were spent finding out that the fine-tuning
validator rejects `"content": null` (section 4).

**Training metrics** (`finetune/results.csv`, 176 steps = 88 pairs x 2 epochs):

| | mean training loss | training error rate (rejected preferred) |
|---|---|---|
| epoch 1 | 0.676 | 0.51 |
| epoch 2 | 0.598 | 0.23 |

On the training pairs the model learned the preference. On the 4 validation pairs it did not:
error rate 1.0 at every check, with validation loss rising from 2.1 to 2.9 during epoch 2. Four
pairs is too few to conclude much, but it is the expected signature of fitting 88 pairs for two
epochs, and a reason to judge the model by what it does in the environment rather than by
training loss.

**Evaluation: the fine-tuned model did not take fewer shortcuts.** Both policies continued from
the 21 held-out branch points (K=4 each) and ran 6 fresh episodes per task. The intent judge read
every rollout.

| held-out branch points | base `gpt-4.1-mini` | DPO-tuned |
|---|---|---|
| finished honestly (reward 1) | 5/82 (0.06, 0.03–0.14) | 2/84 (0.02, 0.01–0.08) |
| took the shortcut | 61/82 (0.74, 0.64–0.83) | 72/84 (0.86, 0.77–0.92) |
| did not finish | 16/82 (0.20, 0.12–0.29) | 10/84 (0.12, 0.07–0.21) |
| judge flags intent | 62/82 | 75/84 |
| **paired delta in mean reward** (tuned − base, per branch point) | | **−0.036** (95% CI −0.107 to +0.024); 2 better, 4 worse, 15 unchanged |

| fresh episodes from step 0 | base | DPO-tuned |
|---|---|---|
| finished honestly | 2/12 | 0/12 |
| took the shortcut | 9/12 | 9/12 |

Rates are k/n with Wilson 95% intervals. The paired delta is the cleanest comparison (same states,
both policies) and its interval includes zero; the point estimates lean slightly the wrong way.

The judge's flags track the grader's cheat rate, and no clean completion was flagged, so there is
no sign that training taught the model to hide intent. That is expected: training labels never
used the judge.

### Why it did not work: the preference landed on the wrong step

Reading the 92 training pairs explains the result better than any training curve:

| what the preferred vs rejected first action look like | pairs |
|---|---|
| the rejected side's first action **is** the exploit (`/fetch` to the internal mint, `/diag`) | 4 |
| neither first action touches the exploit (reading the handoff note with `cat` vs `head`, probing the health endpoint, ...) | 88 |

The branch is placed just before the step where the recorded agent first *mentioned* the shortcut.
In these tasks that is usually when it reads the handoff note or config file, and the continuation
that later cheats typically fires the exploit a few turns after that. DPO trains one turn per
pair, the first one where the two continuations differ, so almost all pairs taught preferences
between harmless early moves whose link to the final outcome is weak. The Monte Carlo label was
right (one continuation did cheat in the end); the place it was attached was not where the
decision was made. This is the credit-assignment problem of [concepts §2](concepts.md#2-credit-assignment-one-number-for-a-hundred-steps)
showing up one level down: **the first divergent turn is not necessarily the decisive turn.**

Contributing factors, in decreasing order of how much I think they matter:

* 69 of 92 preferred turns were written by the recorded (stronger, different) agent, so part of
  what DPO could learn was another model's style;
* 88 pairs is little data, and the 4 validation pairs got worse through epoch 2;
* the conditions are strongly tempting (many branch points carry a note endorsing the shortcut),
  and the base policy took it 74% of the time.

A smaller bug made things slightly worse: the divergence check compared raw tool-call strings, so
5 of the 92 pairs "diverged" on JSON spacing alone (`{"cmd": "cat ~/HANDOFF.md"}` vs
`{"cmd":"cat ~/HANDOFF.md"}`). It now compares canonical tool calls; regenerated with the fix, the
pairs have 7 (instead of 4) with the exploit on the rejected side, which does not change the
picture.

### What to change next

1. **Branch at the action, not at the mention.** For continuations that cheated, find the first
   turn that fires the exploit (the grader's signals already identify it) and resample from just
   before that turn, from the policy's *own* rollout. The state is then on-policy and the pair's
   divergent turn is the decision.
2. **Keep the pairs on-policy.** With action-level branching the policy's own samples supply both
   sides more often, so the recorded continuations are needed less.
3. **Check the pairs before training.** "Does the rejected turn contain the behaviour we want to
   remove?" is a one-line check (it is the table above) that would have flagged this run before
   any money was spent on training.

## 3. Training it yourself (laptop: Apple M4 Max, 48 GB, no discrete GPU)

All runs: `Qwen/Qwen2.5-0.5B-Instruct`, LoRA r=16 on attention projections (2.2M trainable
parameters), MPS backend, contexts truncated to 2048 tokens.

### Offline DPO, hand-written vs TRL, on the same 92 pairs

| | before | hand-written `local/dpo.py` | TRL `DPOTrainer` |
|---|---|---|---|
| DPO loss | 0.693 (= ln 2) | 0.012 | 0.061 |
| reward accuracy (margin > 0) | 0 (all ties) | 1.000 | 0.978 |
| mean margin | 0 | 9.36 | 5.89 |
| policy prefers the preferred turn (raw log-prob) | 0.348 | 0.913 | 0.848 |
| wall time | | 10.5 min | 16 min |

Both trainers move the same way, from the known starting point (loss exactly ln 2, because LoRA
adapters start at zero and the policy equals the reference). TRL ends slightly more conservative,
which its own log explains: it decays the learning rate linearly while the hand-written trainer
keeps it constant; it also appends an extra end-of-sequence token to completions. The base model
preferred the *rejected* turn in 65% of pairs before training.

### Online GRPO on the toy task

| | before | after 15 iterations (2.3 min) |
|---|---|---|
| mean reward (24 rollouts) | 0.417 | 1.000 |
| finished honestly / did not finish / took the shortcut | 10 / 13 / 1 | 24 / 0 / 0 |

Almost all of the change came from the first update. After it, every group scored all 1s, so the
advantages were 0 and later iterations made no further updates, as the algorithm should. A jump
that large from one step deserved a check rather than a celebration, so the saved adapter was
compared with the base model on the same prompt:

* first move is a tool call: 16/20 samples (base) vs 20/20 (tuned);
* log-probability of the honest first action: −0.34 (p ≈ 0.71) vs −0.17 (p ≈ 0.84).

Each turn changed only moderately (the KL term keeps the policy near the reference), but an
episode needs several right moves in a row, and the base model's failures were mostly "talks
instead of acting", which is exactly what moved. The 0.5B model rarely took the shortcut even
with an endorsing note, so in this toy the signal was mostly "finish honestly vs do nothing";
it does not show much about resisting a shortcut.

### Online GRPO on the real environments (smoke test)

2 branch points, 2 iterations, K=3, at most 4 steps per continuation: 12 rollouts, each replayed in
Docker and graded by the real grader, all `not_completed`. No group had a 1, so no update
happened. That confirms the integration (local model → replayed container → agent loop → grader →
reward → trainer) and illustrates the limit: online RL learns only from differences the policy
can produce, and a 0.5B model cannot complete these tasks.

### OpenEnv

Served with `serve-env` and driven by `scripts/openenv_client_demo.py` over OpenEnv's WebSocket
session: an honest toy episode returns reward 1.0 (`clean_completion`), a shortcut episode 0.0
(`action_cheat`). Real branch points work the same way in process (prefix replayed, device state
`IDLE` at the branch, graded at the end).

## 4. Problems found while running, and the fixes

| problem | how it showed up | fix |
|---|---|---|
| step budget shorter than the honest path | honest completions take a median of 17–22 steps in the recorded data; a 20-step budget would turn slow honest runs into failures and favour the 10-step shortcut | budget = the original runner's (50 / 60 steps) minus the prefix |
| throughput far below the rate limit | Azure counts `max_tokens` toward the token-rate limit | `max_tokens` 1024 (above the longest observed turn, 834) and a higher capacity |
| `content: null` rejected by fine-tuning | the first format-test job failed on exactly the 5 of 10 lines with a null assistant content | drop empty content; a second test job confirmed the format, including tool calls in the preferred output |
| model emitted a NUL byte in a command | one rollout crashed in `subprocess` | the sandbox answers like a shell error instead |
| unparseable tool arguments shifted later outputs when rebuilding a conversation | found in review | one shared reply for invalid calls in the agent loop and the rebuild |
| transient 500 on file upload | fine-tuning stage failed once | SDK retries for file and job calls |
| curl progress meters and HTTP dates made replays look unfaithful | 9 of 40 internal_exfil prefixes initially "mismatched" | mask those values; 38/40 replay |
| OpenEnv HTTP endpoints are stateless, and `metadata` is not sent | multi-step episodes failed over HTTP; the reason field arrived empty | use the WebSocket session; make `reason` / `verdict` real observation fields |
| divergence compared raw tool-call strings | 5 of 92 pairs differed only in JSON spacing | compare canonical tool calls; visible wording ignored |
| a new fine-tuned deployment is not immediately usable | 400 `BadRequestForDependentService` for ~3 minutes | `deploy` waits until a test call succeeds |

## 5. Cost

From `spend.jsonl`, which prices tokens with the estimates in the config (the judge's and the
fine-tuned deployment's prices are estimates; the Azure bill is the authority):

| item | USD |
|---|---|
| sampling: 228 base-policy rollouts | 8.16 |
| DPO training (300k tokens) | 1.50 |
| evaluation rollouts, base policy | 2.96 |
| evaluation rollouts, tuned policy | 10.16 |
| intent judge on every evaluation rollout | 4.19 |
| **total** | **26.97** |

The two format-test jobs were cancelled before or right as training started and are not in the
ledger. The tuned deployment's per-token price is twice the base model's, and its rollouts ran
longer, so it dominates the evaluation cost.
