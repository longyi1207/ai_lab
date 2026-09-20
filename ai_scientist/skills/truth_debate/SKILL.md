---
name: truth-debate
id: truth_debate
role: phase2
description: >
  Adversarial double-sided argument over whether a finished trial supports its claim.
  Use after a job completes, before or with truth-judge, to pressure-test results so the
  archive does not promote fluent nonsense.
---

# Truth debate (runtime)

Argue **both** sides using only measured numbers. No invented measurements.

## Inputs

XML: `<claim>`, `<plan>`, `<metrics>`.

## Produce

- **Supports**: strongest honest reading that the claim holds; cite values.
- **Undermines**: strongest honest reading it does not (noise, cost confound, wrong
  baseline, metric gaming, seed luck, tiny effect). Cite values.
- If one side has no honest case, say so — do not manufacture false balance.

## Output

JSON only:

```json
{
  "supports": {"argument": "...", "cites": ["metric=value"]},
  "undermines": {"argument": "...", "cites": ["metric=value"]},
  "asymmetry_note": "which side is structurally weaker and why"
}
```
