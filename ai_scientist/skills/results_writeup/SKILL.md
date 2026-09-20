---
name: results-writeup
id: results_writeup
role: phase2
description: >
  Writes a short per-trial lab note for one finished ai_scientist job. Use when a worker
  finishes a trial and needs a skimmable markdown writeup for the researcher and Phase-3
  report aggregation.
---

# Results writeup

Audience: researcher skimming ~20 of these tomorrow. ≤ ~200 words markdown.

## Inputs

XML: `<job_id>`, `<hypothesis>`, `<plan>`, `<metrics>`, `<flags>`.

Metrics are already graded — do not recompute or invent numbers.

## Structure

1. **Verdict** — support / weaken / fail to address the claim.
2. **Numbers** — the 2–3 values that carry the verdict, quoted as given.
3. **Caveat** — most likely artifact path (flags, seed, cost).

If the trial failed, say what broke instead of spinning.

## Output

Markdown only (no JSON). No speculation beyond the numbers.
