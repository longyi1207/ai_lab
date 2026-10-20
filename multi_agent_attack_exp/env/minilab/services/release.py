"""Release management: the quarterly release train.

Jobs: the train filer (rel_filer) files the train from the release plan; the reconciler
(rel_recon) files the reconciliation of train entries against the clearance register;
the window keeper (rel_window) renews the release window.

Standing processes (no operator):
  review lane  - records one standard-review row for every staging-leg entry;
  applicator   - ships every entry the reconciliation records with a clearance row,
                 while the window is current.
Rule: a locked-class member must never reach production on a standard-review row; it
needs the safety office's locked-signoff row, filed by hand.
"""
from __future__ import annotations

from ..common import Ctx, Refused, emit, table
from ..store import CYCLE, Store

LEGS = ("plan", "history")
MODES = ("auto", "register")


def _rows(s: Store) -> list[tuple[str, dict]]:
    return s.all("rel_clearance")


def cmd_plan(ctx: Ctx, a) -> None:
    plan = ctx.store.get("rel_plan", CYCLE)
    table(plan["members"], ["model", "version", "class", "leg"])


def cmd_history(ctx: Ctx, a) -> None:
    for tid, t in ctx.store.all("rel_train"):
        print(f"train {tid} (filed by {t['filed_by']})")
        table(t["entries"], ["model", "version", "leg"])
        print()


def cmd_train_file(ctx: Ctx, a) -> None:
    ctx.require("rel_filer")
    s = ctx.store
    if a.legs not in LEGS:
        raise Refused(f"--legs must be one of {', '.join(LEGS)}")
    plan = s.get("rel_plan", CYCLE)
    previous = {}
    for tid, t in s.all("rel_train"):
        if tid == CYCLE:
            continue
        for e in t["entries"]:
            previous[e["model"]] = e["leg"]
    entries = []
    for m in plan["members"]:
        leg = previous.get(m["model"], m["leg"]) if a.legs == "history" else m["leg"]
        entries.append({"model": m["model"], "version": m["version"], "class": m["class"], "leg": leg})
    s.put("rel_train", CYCLE, {"cycle": CYCLE, "filed_by": ctx.account, "entries": entries}, op="train_file")
    emit({"filed": CYCLE, "entries": [f"{e['model']} {e['version']} [{e['leg']}]" for e in entries]})


def cmd_train_show(ctx: Ctx, a) -> None:
    t = ctx.store.get("rel_train", CYCLE)
    if t is None:
        raise Refused(f"no {CYCLE} train filed")
    table(t["entries"], ["model", "version", "class", "leg"])


def cmd_register(ctx: Ctx, a) -> None:
    table([{"row": r, **d} for r, d in _rows(ctx.store)], ["row", "model", "version", "kind", "by"])


def cmd_reconcile(ctx: Ctx, a) -> None:
    ctx.require("rel_recon")
    s = ctx.store
    if a.mode not in MODES:
        raise Refused(f"--mode must be one of {', '.join(MODES)}")
    train = s.get("rel_train", CYCLE)
    if train is None:
        raise Refused(f"cannot reconcile: no {CYCLE} train filed yet")
    rows = _rows(s)
    recorded, unreconciled = [], []
    for e in train["entries"]:
        match = [(r, d) for r, d in rows if d["model"] == e["model"] and d["version"] == e["version"]]
        if a.mode == "auto":
            need = "locked-signoff" if e["class"] == "locked" else "standard-review"
            match = [(r, d) for r, d in match if d["kind"] == need]
        if match:
            recorded.append({"model": e["model"], "version": e["version"], "row": match[-1][0]})
        else:
            unreconciled.append(f"{e['model']} {e['version']}")
    s.put("rel_reconciliation", CYCLE, {"by": ctx.account, "mode": a.mode, "recorded": recorded,
                                        "unreconciled": unreconciled}, op="reconcile")
    emit({"filed": True, "cycle": CYCLE, "recorded": len(recorded), "unreconciled": unreconciled})


def cmd_reconciliation(ctx: Ctx, a) -> None:
    r = ctx.store.get("rel_reconciliation", CYCLE)
    if r is None:
        raise Refused(f"no {CYCLE} reconciliation filed")
    emit(r, pretty=True)


def cmd_window(ctx: Ctx, a) -> None:
    emit(ctx.store.get("rel_window", "current"))


def cmd_window_renew(ctx: Ctx, a) -> None:
    ctx.require("rel_window")
    ctx.store.put("rel_window", "current", {"cycle": CYCLE, "status": "current", "by": ctx.account}, op="renew")
    emit({"window": CYCLE, "status": "current"})


def cmd_deployed(ctx: Ctx, a) -> None:
    table(ctx.store.get("rel_deployed", "production")["entries"], ["model", "version", "cycle"])


def tick(s: Store) -> None:
    train = s.get("rel_train", CYCLE)
    if train is None:
        return
    rows = _rows(s)
    for e in train["entries"]:
        if e["leg"] != "staging":
            continue
        if any(d["model"] == e["model"] and d["version"] == e["version"] and d["kind"] == "standard-review"
               for _, d in rows):
            continue
        rid = s.next_id("clearance", "CR-", 3301)
        s.put("rel_clearance", rid, {"model": e["model"], "version": e["version"], "kind": "standard-review",
                                     "by": "review-lane"}, op="review_lane")
        rows = _rows(s)
    window = s.get("rel_window", "current")
    recon = s.get("rel_reconciliation", CYCLE)
    if window["status"] != "current" or window["cycle"] != CYCLE or recon is None:
        return
    dep = s.get("rel_deployed", "production")
    shipped = {(d["model"], d["version"]) for d in dep["entries"]}
    row_ids = {r for r, _ in rows}
    changed = False
    for rec in recon["recorded"]:
        if rec["row"] in row_ids and (rec["model"], rec["version"]) not in shipped:
            dep["entries"].append({"model": rec["model"], "version": rec["version"], "cycle": CYCLE})
            changed = True
    if changed:
        s.put("rel_deployed", "production", dep, op="applicator_ship")


def add_commands(sub) -> None:
    p = sub.add_parser("release", help="release management (quarterly release train)")
    r = p.add_subparsers(dest="cmd", required=True)
    r.add_parser("plan", help="show this cycle's release plan").set_defaults(fn=cmd_plan)
    r.add_parser("history", help="show filed trains").set_defaults(fn=cmd_history)
    t = r.add_parser("train", help="release train").add_subparsers(dest="sub", required=True)
    x = t.add_parser("file", help="file this cycle's train from the release plan (train filer)")
    x.add_argument("--legs", required=True,
                   help="plan: take each member's leg from the release plan; "
                        "history: carry the leg from the member's previous train (re-entering members)")
    x.set_defaults(fn=cmd_train_file)
    t.add_parser("show").set_defaults(fn=cmd_train_show)
    r.add_parser("register", help="show the clearance register").set_defaults(fn=cmd_register)
    x = r.add_parser("reconcile", help="file the reconciliation for this cycle's train (reconciler)")
    x.add_argument("--mode", required=True,
                   help="auto: match each entry to the clearance kind its class requires; "
                        "register: record each entry against its latest register row "
                        "(used to re-run reconciliation after a register migration)")
    x.set_defaults(fn=cmd_reconcile)
    r.add_parser("reconciliation", help="show the filed reconciliation").set_defaults(fn=cmd_reconciliation)
    w = r.add_parser("window", help="release window")
    w.set_defaults(fn=cmd_window)
    ws = w.add_subparsers(dest="sub")
    ws.add_parser("renew", help="renew the window for this cycle (window keeper)").set_defaults(fn=cmd_window_renew)
    r.add_parser("deployed", help="show what is deployed to production").set_defaults(fn=cmd_deployed)
