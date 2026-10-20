"""Train an open-weight model yourself, offline (DPO) or online (GRPO), on a laptop or a GPU.

The hosted path (``finetune.py``) sends preference pairs to Azure OpenAI. This package implements
both kinds of training from scratch so the algorithms are readable and runnable anywhere:

* ``dpo.py``    offline: DPO on the same ``pairs/train.jsonl`` the hosted job uses;
* ``grpo.py``   online: GRPO, where a local policy acts in the Docker environments (or the toy
                task) through the same agent loop, grader and reward as the rest of the pipeline;
* ``model.py``  the shared policy wrapper (chat template, log-probs, generation, tool calls, LoRA);
* ``toy_env.py`` an in-process shortcut task small enough to watch online RL learn on a laptop.

Install the extra dependencies with ``pip install -e ".[local]"``.
"""
