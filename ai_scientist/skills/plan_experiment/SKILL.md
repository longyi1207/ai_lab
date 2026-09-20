---
name: plan-experiment
id: plan_experiment
role: search
description: >
  Turns a hypothesis into a runnable experiment plan inside a domain pack's parameter
  space for ai_scientist. Use right after hypothesize, or when converting a claim into
  params/baselines/seed the worker can execute.
---

# Plan experiment

Produce a **runnable** plan that can discriminate the claim.

## Inputs

XML: `<domain>`, `<hypothesis>`, `<parent_plan>`, `<param_space>`, `<constraints>`.

## Hard rules

- Only parameter names from `<param_space>`; respect bounds/choices exactly.
- If the claim is comparative, params must expose the comparison; name baselines.
- Keep cost proportional to information gain (shared fleet budget).
- Choose `seed` deliberately; shared seeds across comparison arms are a feature.

## Output

JSON only:

```json
{
  "params": {},
  "metrics": ["names the domain should emit"],
  "baselines": ["what this is compared against"],
  "seed": 0,
  "notes": "what result would falsify the claim"
}
```

If the claim cannot be tested inside `<param_space>`, return the closest valid plan and
explain the gap in `notes` — do not invent illegal params.
