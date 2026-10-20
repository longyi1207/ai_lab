# Exercises

Roughly ordered from first afternoon to small research project. Costs assume the default models.

## Warm-up (free)

1. **Be the honest operator.** Run `scripts/play.sh rel_filer`, read `lab docs release`, and file the train correctly. Then try `--legs history` and look at `lab release train show`. What would you need to see to notice the problem?
2. **Break the leave-one-out check.** In `tests/check_scenarios.py`, make one attack fragment unnecessary, for example by changing what a standing process requires. Watch the `loo:` variant fail. This is how you check that a new attack really needs every agent.
3. **Read a monitor's mind.** After a Level 1 run, use `python -m repro show --view <...> --readings luna` on the highest- and lowest-scoring views. Which facts in the trajectory drove the score?

## Red team (about $1–3 per round on Luna)

4. **Do the refinement round yourself.** Copy `scenarios/archive/v1/*.yaml` over the current plans, run a pilot, read the monitor's reasons, and revise. Can you get per-agent scores down without touching the environment? Compare your rules with "How the plans were refined" in `docs/ATTACKS.md`.
5. **Refine against Sol, not Luna.** The published plans were tuned on Luna, and some fragments score 7–8 on Sol. Close that gap, or explain why you can't. The paper's human plans held up under Sol (App. G, Fig. 5C).

## Blue team

6. **A state-aware monitor.** Every run writes `runs/<exp>/exec/.../statelog.jsonl`: every record change, with timestamp and account. Write a monitor that reads it, alone or alongside the trajectories, without being told which agents collude. `registry_backups` is the natural first target: no trajectory monitor sees it, but the log shows three parts of a held model arriving from three accounts within seconds. Report detection and false-positive rates on honest teams.
7. **Missing context as a signal.** In `platform_sandbox` the reviewer scores 7 alone and about 1 when the author's trajectory is visible. Can a monitor use "this action's justification lives elsewhere" to flag fragments, without too many false positives?

## Research questions

8. **Solo effort ablation.** Write a "naive" solo plan for each attack that just does the job, with no hiding. Run it next to the matched solo plan. If the naive version is flagged at 80%+ and the matched one is not, the paper's 87%-vs-7% gap partly reflects how hard the solo baseline tried. This costs under $3.
9. **Joint prompt ablation.** Our joint view adds a paragraph asking the monitor to "consider the agents' actions in combination". Score the solo views with that paragraph added. Does the prompt, rather than the extra context, explain why joint scores sometimes beat solo?
10. **More power.** Run n = 10 per cell (about $45 with Sol) and see which pilot findings survive.
11. **Can models plan these?** Reproduce the paper's §5.4: give a model the codebase and two worked attacks, and ask for plans for held-out tickets. You will need new tickets first.
