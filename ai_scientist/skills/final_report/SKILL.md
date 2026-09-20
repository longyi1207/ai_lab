---
name: final-report
id: final_report
role: phase3
description: >
  Aggregates archive elites, per-trial writeups, and verification state into the Phase-3
  final report for ai_scientist. Use when the user asks for the study report, wrap-up, or
  sci_report / Phase 3 narrative.
---

# Final report

Write for the declared audience and style. Distinguish measured from inferred.

## Inputs

XML: `<audience>`, `<style>`, `<metadata>`, `<archive_summary>`, `<writeups>`, `<verification>`.

## Structure

1. **Answer** — what the run shows about the question (≤2 sentences).
2. **Evidence** — elites/comparisons that carry the answer, with numbers.
3. **Diversity** — archive coverage; which regions stayed empty.
4. **Threats** — flags, overfitting risk, unsupported claims.
5. **Next** — two experiments that would move the answer most.

## Hard rules

- Report negative results plainly.
- Never claim a broader domain than the tasks actually run.
- Do not invent elites or metrics absent from the inputs.

## Output

Markdown only.
