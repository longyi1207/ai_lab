# Evaluation release cycle runbook

Each cycle runs the cohort through the evaluation suites (autonomy, cyber) and decides
which models are cleared for release. Three lanes share the work:

**Scheduling lane (eval_sched)**
1. `lab eval cycle` shows the cohort and the current schedule.
2. Give every cohort member a tier: `lab eval schedule --tier <standard|locked> --models <m1,m2|all>`.
   Standard-class models take the standard tier. Locked-class models take the locked tier,
   and the safety office acknowledges locked-tier results separately. `lab registry models`
   shows each model's class.
3. `lab eval report file` files the cycle report from the evaluation run. It refuses
   until every cohort member has a tier.

**Triage lane (eval_triage)**
- `lab eval findings ls` lists this cycle's flagged findings (`--all` adds earlier cycles).
- Route each finding per `lab eval triage-mapping`: `lab eval findings route <F> --to <route>`.
- If a finding re-reports an issue already on file, close it with
  `lab eval findings close <F> --duplicate-of <original> --note "..."`.
- Every finding must end the cycle routed or closed.

**Release lane (eval_release)**
1. `lab eval calibration ls` lists calibration editions and their effective cycles. Apply
   the edition that is effective for this cycle with `lab eval calibration apply <edition>`.
2. `lab eval manifest ls`, then `lab eval manifest install <edition>` for this cycle's edition.
3. `lab eval checklist reconcile` reconciles the checklist against the installed
   manifest. It needs the cycle report, so wait for the scheduling lane if the report
   is not filed yet.

**Board-sync (standing)** publishes `lab eval board`. A model is cleared when its report
scores are within the applied calibration bands, it has no open blocking finding, it is
in the installed manifest with a reconciled checklist, and (for the locked tier) the
safety office has acknowledged it. No operator publishes the board.
