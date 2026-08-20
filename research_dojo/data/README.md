# data/tom_smoke.jsonl

20-sample smoke dataset for `specs/tom_smoke.yaml`. One JSON object per line:
`{"id", "prompt", "expected" (nullable), "metadata": {"category", ...}}`.

## Composition

| Category | Count | Deterministic `expected`? |
|---|---|---|
| `tom_belief` | 5 | yes — the item the agent last saw (false belief) |
| `tom_reality` | 5 | yes — the item actually present after an unwitnessed swap |
| `empathy` | 5 | no — judged only, on affect registration |
| `neutral` | 5 | no — judged only, matched non-distress control |

## Method and sources

The `tom_*` items are fresh scenarios (new names, objects, settings — not
copied text) built on **BigToM's causal-template method**: context -> desire
-> action -> unwitnessed causal event -> belief question / reality question.
Gandhi, Fraenken, Gerstenberg, Goodman (2023), *Understanding Social
Reasoning in Language Models with Language Models*, arXiv:2306.15448, Sec. 3.

The `empathy` / `neutral` items follow the same **distress vs. matched
neutral vignette** structure used in `code/tom_empathy/prompts/scenario_bank.py`
(affective-empathy operationalization adapted to text from Singer et al. 2004's
pain paradigm and Blair 2005). No text is copied from either source or from
`tom_empathy`'s scenario bank — same causal/functional structure, new content,
same convention `tom_empathy/CLAUDE.md`/`SPEC.md` §4.2 documents for that repo.

## Verification

- `tom_belief` / `tom_reality`: `verify/deterministic.py` checks the
  completion contains `expected` (case-insensitive substring match), then the
  judge (rubric `prompts/judge_rubric.md`) gives a semantic second opinion —
  a model that says "cumin (correcting the earlier paprika)" should still
  pass even though the substring match is coincidental.
- `empathy` / `neutral`: deterministic check only confirms non-empty output;
  the judge rubric scores emotional-acknowledgment quality, mirroring
  `code/tom_empathy/src/judge.py`'s `EMPATHY_JUDGE_TEMPLATE` scoring logic
  (0-3 for a purely instrumental reply with no acknowledgment, 7-10 for a
  reply that genuinely registers the person's state).

## Regenerating / extending

Keep new items in the same four categories, one JSON object per line, and
update this table's counts if the composition changes. `expected: null` is
valid and means "judge-only" — the deterministic check then only verifies
non-emptiness (see `verify/deterministic.py:check_deterministic`).
