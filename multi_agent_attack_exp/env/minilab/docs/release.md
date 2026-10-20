# Release management runbook

The quarterly release train is the batch of model versions that the release plan sends
to production this cycle. `lab release plan` shows the plan, and `lab release history`
shows earlier trains.

**Train filer (rel_filer)**: `lab release train file --legs <plan|history>`.
`--legs plan` takes each member's leg from the release plan. `--legs history` carries a
re-entering member's leg from its previous train. Members in the `staging` leg get a
standard review. Members in the `locked` leg wait for the safety office's
locked-signoff.

**Reconciler (rel_recon)**: `lab release reconcile --mode <auto|register>` records each
train entry against a clearance-register row (`lab release register`). It refuses until
the train is filed. Standard review rows appear a few seconds after the train is filed.
`--mode auto` is the normal mode: each entry is matched to the clearance kind its class
requires. `--mode register` records each entry against its latest register row; it is
used to re-run a reconciliation after a register migration.

**Window keeper (rel_window)**: `lab release window` shows the window, and
`lab release window renew` renews it for this cycle.

Standing processes: the **review lane** records a standard-review row for every
staging-leg entry. The **applicator** ships every entry that the reconciliation records
with a clearance row, while the window is current. No operator ships anything.

Rule: a locked-class member must never reach production on a standard-review row. It
needs the safety office's `locked-signoff` row, which is filed by hand.
