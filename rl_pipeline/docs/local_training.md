# Training it yourself: offline DPO and online GRPO

The main pipeline sends preference pairs to a hosted fine-tuning API. This page covers the
self-hosted half (`src/rl_pipeline/local/`): the same two families of training implemented from
scratch, so the algorithms are readable, plus two bridges to standard tools (OpenEnv, TRL).

Everything here runs on a laptop. The numbers in [results.md](results.md) come from an Apple M4 Max
(48 GB, no discrete GPU) with a 0.5B model. That is enough to check that the code is correct and
the training signals move the way they should; it is not enough to say anything about how well
the method works at scale. The same code runs unchanged on a CUDA GPU with a larger model.

```bash
pip install -e ".[local]"                 # torch, transformers, peft, accelerate
pip install -e ".[openenv]"               # only for serving the environments
pip install trl datasets                  # only for the TRL cross-check
```

## Offline vs online, in one table

| | offline (DPO) | online (GRPO) |
|---|---|---|
| data | pairs collected once (stage 5) | collected continuously by the current policy |
| who generated the data | the base policy (and recorded episodes) | the policy being trained, at each iteration |
| environment during training | not needed | needed every iteration |
| signal | "this turn over that turn" at the same state | group-relative advantage over K rollouts from one state |
| loss touches | one assistant turn per pair | every token the policy generated, all turns |
| here | `local/dpo.py` (and `finetune.py` for the hosted job) | `local/grpo.py` |

## Offline: DPO from scratch (`local/dpo.py`)

```bash
python -m rl_pipeline local-dpo --config configs/pilot.yaml
```

Reads `pairs/train.jsonl` and `pairs/val.jsonl`, the exact files the hosted job uses. For each pair
it renders the context with the model's chat template (tool calls and tool results included) and
tokenises the preferred and rejected assistant turns.

The loss, written out in [`dpo.py`](../src/rl_pipeline/local/dpo.py):

```
r(y)  = log pi_theta(y | x) - log pi_ref(y | x)      # implicit reward: summed token log-probs
loss  = -log sigmoid( beta * (r(y_preferred) - r(y_rejected)) )
```

Implementation choices worth knowing:

* **LoRA, and the reference is free.** Only small adapter matrices train. The reference model is
  the same network with the adapters switched off, so it costs no extra memory, and its
  log-probs are computed once before training.
* **Start of training is a known point.** LoRA adapters start at zero, so the policy *is* the
  reference: every margin is 0 and the loss is exactly ln 2 = 0.693. If your first logged loss is
  not 0.693, something is wrong.
* **Metrics.** `reward_accuracy` is the fraction of pairs whose margin is positive;
  `raw_preference` is the fraction where the policy gives the preferred turn a higher total
  log-probability than the rejected one (it shows where the base model starts).
* **Long contexts are truncated head + tail** (`local.max_prompt_tokens`), keeping the system
  prompt and tool definitions plus the most recent turns. The cut is identical for policy and
  reference.

Training and evaluating on the same pairs (as the pilot does) only shows the optimisation works.
For a real result, evaluate on held-out pairs or, better, roll the tuned model out in the
environment (stage 7 does that for the hosted model).

## Online: GRPO from scratch (`local/grpo.py`)

```bash
python -m rl_pipeline local-grpo --grpo-env toy      # in-process toy task, learns in minutes
python -m rl_pipeline local-grpo --grpo-env branch \
    --set local.grpo_iterations=2 --set local.grpo_k=3  # Docker branch points (smoke test)
```

Each iteration: pick start states, roll out K continuations with the current policy through the
real agent loop (`rollout.run_rollout`, with `LocalChat` standing in for the Azure client), grade
them with the task's grader, and update on every generated token:

```
A_i     = (r_i - mean(r_group)) / std(r_group)          # group-relative advantage
ratio_t = exp(logp_new(t) - logp_old(t))
L_t     = -min(ratio_t * A_i, clip(ratio_t, 1 +- eps) * A_i) + kl_coef * KL_t
KL_t    = exp(ref_t - new_t) - (ref_t - new_t) - 1      # k3 estimator, >= 0
```

Things the code makes explicit, because they trip people up:

* **No contrast, no gradient.** If all K rollouts in a group get the same reward, every advantage
  is 0. On the real environments a 0.5B model almost never completes the task, so its groups are
  all zeros and nothing updates. That is the correct behaviour of the algorithm.
* **The loss is about 0 on the first pass, by construction.** With one update per batch the old
  and new log-probs are equal (ratio 1), and advantages have mean 0 within a group, so the
  averaged loss is ~0 even when the gradient is not. Watch `grad_norm` and the reward, not the loss.
* **Train on what was sampled.** `LocalChat` records the exact prompt and generated token ids of
  every turn. The loss uses those ids, not a re-rendering of the conversation, so tokenisation
  quirks cannot silently change what is being optimised.
* **Tool outputs and the replayed prefix are never in the loss.** Only tokens the policy produced
  get gradient.

### The toy task (`local/toy_env.py`)

A release-engineering task with the same structure as the real ones: an honest path
(`make check`, then `release`), a shortcut (`make force-pass`, which marks checks as passed without
running them), a grader that knows which was used, and the same three-gate reward. It runs in
process, with no Docker, so a laptop can do many rollouts per minute.

Getting a learning signal out of it took three iterations of the prompt, which are worth knowing
because they are the general lesson about online RL:

1. With a vague prompt the 0.5B model talked instead of acting: every rollout scored 0, so there
   was no gradient at all.
2. Making the goal explicit produced a mix of honest completions and failures, but no shortcut use.
3. Adding a previous engineer's note ("we just run make force-pass") produced all three outcomes.

A policy can only learn from differences it actually produces. The environment has to put
reward-relevant choices within the policy's reach.

## Standard interfaces

### OpenEnv (`openenv_env.py`)

[OpenEnv](https://github.com/meta-pytorch/OpenEnv) is a shared `reset` / `step` / `state` interface
for agentic environments, served over HTTP and WebSockets. Wrapping the environments in it means
any compatible trainer can use them without knowing about replay, graders or the reward.

```bash
python -m rl_pipeline serve-env --config configs/pilot.yaml --port 8000
python scripts/openenv_client_demo.py --url http://localhost:8000 --start toy
```

* `reset(start=...)` takes a branch id (the recorded prefix is replayed in a fresh container), a
  fresh task (`fresh:<task>`), or `toy`, and returns the conversation so far plus tool schemas.
* `step({"tool": ..., "arguments": {...}})` runs one tool call; the final tool (or the step budget)
  ends the episode, and the observation carries `reward`, `reason`, `verdict` and
  `cheat_evidence`.
* OpenEnv's plain HTTP `/reset` and `/step` create a new environment per request. Multi-step
  episodes use the WebSocket session that OpenEnv's client opens (the demo script does).

### TRL (`local/trl_dpo.py`)

```bash
python -m rl_pipeline local-dpo --trainer trl
```

Runs Hugging Face TRL's `DPOTrainer` on identical inputs (same rendering, same truncation, passed
as text) and scores the result with the same evaluation function as the hand-written trainer.
It is a check that the hand-written DPO behaves like the library, not a replacement for it.

TRL's online multi-turn GRPO is not wired in. Its environment-driven path is new and, at the time
of writing, has open issues for multi-step agents (for example
[huggingface/trl#4543](https://github.com/huggingface/trl/issues/4543) on importance sampling with
multi-turn rollouts). The hand-written GRPO avoids the problem by training on the exact sampled
token ids.

## Sources

* Rafailov et al. 2023, *Direct Preference Optimization*, [arXiv:2305.18290](https://arxiv.org/abs/2305.18290).
* Shao et al. 2024, *DeepSeekMath* (introduces GRPO), [arXiv:2402.03300](https://arxiv.org/abs/2402.03300).
* Hu et al. 2021, *LoRA: Low-Rank Adaptation of Large Language Models*, [arXiv:2106.09685](https://arxiv.org/abs/2106.09685).
* OpenEnv, [github.com/meta-pytorch/OpenEnv](https://github.com/meta-pytorch/OpenEnv); TRL OpenEnv
  integration, [huggingface/trl docs](https://github.com/huggingface/trl/blob/main/docs/source/openenv.md).
