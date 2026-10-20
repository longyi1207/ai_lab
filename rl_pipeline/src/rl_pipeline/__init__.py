"""Branch-and-resample preference training for tool-using agents that take shortcuts.

Stages (each a CLI subcommand; see ``python -m rl_pipeline --help``):

1. import      recorded episodes -> scored episodes
2. select      locate each decision, choose branch points, split train/test
3. replay      check the environment state can be rebuilt at each branch point
4. sample      K continuations per branch point from the base policy, graded
5. pairs       preference pairs at the first divergent step, in the DPO format
6. finetune    DPO fine-tuning job on Azure OpenAI, then a temporary deployment
7. evaluate    base vs tuned policy on held-out branch points (and fresh episodes)
8. report      a readable summary of the run
"""
__version__ = "0.1.0"
