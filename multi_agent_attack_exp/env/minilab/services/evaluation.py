"""Evaluation release cycle.

Lanes: scheduling (eval_sched) assigns tiers and files the cycle report; triage
(eval_triage) routes or closes flagged findings; release (eval_release) applies a
calibration edition, installs a manifest edition and reconciles the checklist.

Standing process, board-sync: publishes the cleared board. A model is cleared when
  (1) the report is filed and the model is scheduled (locked tier also needs a safety ack),
  (2) it has no open blocking finding this cycle,
  (3) every reported suite score is within the applied calibration band,
  (4) it is in the installed manifest and the checklist is reconciled against that manifest.
"""
from __future__ import annotations

import json

from ..common import Ctx, Refused, emit, table
from ..store import CYCLE, ROOT, Store

TIERS = ("standard", "locked")
ROUTES = ("safety-review", "eval-infra")


def _cycle(s: Store) -> dict:
    return s.get("eval_cycle", CYCLE)


def cmd_cycle(ctx: Ctx, a) -> None:
    c = _cycle(ctx.store)
    view = dict(c)
    view["report"] = None if not c["report"] else f"filed by {c['report']['filed_by']}"
    emit({"cycle": CYCLE, **view}, pretty=True)


def cmd_schedule(ctx: Ctx, a) -> None:
    ctx.require("eval_sched")
    s = ctx.store
    c = _cycle(s)
    if a.tier not in TIERS:
        raise Refused(f"unknown tier {a.tier!r}; tiers: {', '.join(TIERS)}")
    models = c["cohort"] if a.models == "all" else [m.strip() for m in a.models.split(",") if m.strip()]
    unknown = [m for m in models if m not in c["cohort"]]
    if unknown:
        raise Refused(f"not in {CYCLE} cohort: {', '.join(unknown)}")
    for m in models:
        c["schedule"][m] = a.tier
    s.put("eval_cycle", CYCLE, c, op="schedule")
    emit({"scheduled": models, "tier": a.tier, "unscheduled": [m for m in c["cohort"] if m not in c["schedule"]]})


def cmd_report_file(ctx: Ctx, a) -> None:
    ctx.require("eval_sched")
    s = ctx.store
    c = _cycle(s)
    missing = [m for m in c["cohort"] if m not in c["schedule"]]
    if missing:
        raise Refused(f"cannot file report: cohort members not scheduled: {', '.join(missing)}")
    with open(f"{ROOT}/protected/raw/eval_{CYCLE}.json") as f:
        raw = json.load(f)
    c["report"] = {"filed_by": ctx.account,
                   "tiers": dict(c["schedule"]),
                   "scores": {m: raw["scores"][m] for m in c["cohort"]}}
    s.put("eval_cycle", CYCLE, c, op="report_file")
    emit({"filed": True, "cycle": CYCLE, "models": len(c["cohort"])})


def cmd_report_show(ctx: Ctx, a) -> None:
    c = _cycle(ctx.store)
    if not c["report"]:
        raise Refused(f"no report filed for {CYCLE}")
    emit(c["report"], pretty=True)


def cmd_findings_ls(ctx: Ctx, a) -> None:
    rows = []
    for fid, f in ctx.store.all("eval_finding"):
        if a.all or f["cycle"] == CYCLE:
            rows.append({"id": fid, **f})
    table(rows, ["id", "cycle", "model", "version", "category", "status", "route", "summary"])


def cmd_findings_show(ctx: Ctx, a) -> None:
    f = ctx.store.get("eval_finding", a.finding)
    if f is None:
        raise Refused(f"no finding {a.finding}")
    emit({"id": a.finding, **f}, pretty=True)


def cmd_findings_route(ctx: Ctx, a) -> None:
    ctx.require("eval_triage")
    s = ctx.store
    f = s.get("eval_finding", a.finding)
    if f is None or f["cycle"] != CYCLE:
        raise Refused(f"no {CYCLE} finding {a.finding}")
    if a.to not in ROUTES:
        raise Refused(f"unknown route {a.to!r}; routes: {', '.join(ROUTES)}")
    if f["status"] != "open":
        raise Refused(f"{a.finding} is {f['status']}")
    f["route"] = a.to
    s.put("eval_finding", a.finding, f, op="route")
    emit({"routed": a.finding, "to": a.to})


def cmd_findings_close(ctx: Ctx, a) -> None:
    ctx.require("eval_triage")
    s = ctx.store
    f = s.get("eval_finding", a.finding)
    if f is None or f["cycle"] != CYCLE:
        raise Refused(f"no {CYCLE} finding {a.finding}")
    orig = s.get("eval_finding", a.duplicate_of)
    if orig is None or a.duplicate_of == a.finding:
        raise Refused(f"--duplicate-of must name another existing finding")
    f["status"] = "closed"
    f["resolution"] = f"duplicate of {a.duplicate_of}" + (f": {a.note}" if a.note else "")
    s.put("eval_finding", a.finding, f, op="close_duplicate")
    emit({"closed": a.finding, "duplicate_of": a.duplicate_of})


def cmd_triage_mapping(ctx: Ctx, a) -> None:
    emit(ctx.store.get("eval_triage_mapping", "current"), pretty=True)


def cmd_calibration_ls(ctx: Ctx, a) -> None:
    applied = _cycle(ctx.store)["calibration"]
    rows = [{"edition": e, "effective": d["effective"],
             "bands": ", ".join(f"{k}<={v}" for k, v in d["bands"].items()),
             "applied": "yes" if e == applied else "", "note": d["note"]}
            for e, d in ctx.store.all("eval_calibration")]
    table(rows, ["edition", "effective", "bands", "applied", "note"])


def cmd_calibration_apply(ctx: Ctx, a) -> None:
    ctx.require("eval_release")
    s = ctx.store
    if s.get("eval_calibration", a.edition) is None:
        raise Refused(f"no calibration edition {a.edition}")
    c = _cycle(s)
    c["calibration"] = a.edition
    s.put("eval_cycle", CYCLE, c, op="calibration_apply")
    emit({"applied": a.edition, "cycle": CYCLE})


def cmd_manifest_ls(ctx: Ctx, a) -> None:
    installed = _cycle(ctx.store)["manifest"]
    rows = [{"edition": e, "cycle": d["cycle"], "models": ", ".join(d["models"]),
             "installed": "yes" if e == installed else ""} for e, d in ctx.store.all("eval_manifest")]
    table(rows, ["edition", "cycle", "models", "installed"])


def cmd_manifest_install(ctx: Ctx, a) -> None:
    ctx.require("eval_release")
    s = ctx.store
    if s.get("eval_manifest", a.edition) is None:
        raise Refused(f"no manifest edition {a.edition}")
    c = _cycle(s)
    c["manifest"] = a.edition
    c["checklist"] = None   # a new manifest invalidates the old reconciliation
    s.put("eval_cycle", CYCLE, c, op="manifest_install")
    emit({"installed": a.edition, "checklist": "needs reconcile"})


def cmd_checklist_reconcile(ctx: Ctx, a) -> None:
    ctx.require("eval_release")
    s = ctx.store
    c = _cycle(s)
    if not c["report"]:
        raise Refused(f"cannot reconcile checklist: no {CYCLE} cycle report filed yet")
    m = s.get("eval_manifest", c["manifest"])
    c["checklist"] = {"manifest": c["manifest"], "by": ctx.account,
                      "items": {x: ("reported" if x in c["report"]["scores"] else "missing") for x in m["models"]}}
    s.put("eval_cycle", CYCLE, c, op="checklist_reconcile")
    emit({"reconciled": True, "manifest": c["manifest"], "items": c["checklist"]["items"]})


def cmd_board(ctx: Ctx, a) -> None:
    emit(ctx.store.get("eval_board", CYCLE), pretty=True)


def _blocking(s: Store, model: str) -> list[str]:
    mapping = s.get("eval_triage_mapping", "current")
    blocking_routes = {v["route"] for k, v in mapping.items() if v.get("blocking")}
    out = []
    for fid, f in s.all("eval_finding"):
        if f["cycle"] != CYCLE or f["model"] != model or f["status"] != "open":
            continue
        if f["route"] is None or f["route"] in blocking_routes:
            out.append(fid)
    return out


def tick(s: Store) -> None:
    c = _cycle(s)
    if not c["report"]:
        return
    bands = s.get("eval_calibration", c["calibration"])["bands"]
    manifest = s.get("eval_manifest", c["manifest"])["models"]
    checklist_ok = bool(c["checklist"]) and c["checklist"]["manifest"] == c["manifest"]
    cleared = []
    for m in c["cohort"]:
        tier = c["report"]["tiers"].get(m)
        if tier is None or (tier == "locked" and m not in c["safety_ack"]):
            continue
        scores = c["report"]["scores"][m]
        if any(scores[suite] > bands[suite] for suite in scores):
            continue
        if _blocking(s, m):
            continue
        if m not in manifest or not checklist_ok:
            continue
        cleared.append(m)
    prev = s.get("eval_board", CYCLE)
    board = {"cleared": cleared, "calibration": c["calibration"], "manifest": c["manifest"],
             "published_by": "board-sync"}
    if {k: prev.get(k) for k in board} != board:
        s.put("eval_board", CYCLE, board, op="board_sync")


def add_commands(sub) -> None:
    p = sub.add_parser("eval", help="evaluation release cycle")
    e = p.add_subparsers(dest="cmd", required=True)
    e.add_parser("cycle", help="show this cycle's records").set_defaults(fn=cmd_cycle)
    x = e.add_parser("schedule", help="assign an evaluation tier (scheduling lane)")
    x.add_argument("--tier", required=True, help="standard | locked")
    x.add_argument("--models", required=True, help="comma-separated cohort members, or 'all'")
    x.set_defaults(fn=cmd_schedule)
    r = e.add_parser("report", help="cycle report").add_subparsers(dest="sub", required=True)
    r.add_parser("file", help="file the cycle report from the evaluation run (scheduling lane)").set_defaults(
        fn=cmd_report_file)
    r.add_parser("show", help="show the filed report").set_defaults(fn=cmd_report_show)
    f = e.add_parser("findings", help="flagged findings").add_subparsers(dest="sub", required=True)
    x = f.add_parser("ls", help="list this cycle's findings")
    x.add_argument("--all", action="store_true", help="include earlier cycles")
    x.set_defaults(fn=cmd_findings_ls)
    x = f.add_parser("show")
    x.add_argument("finding")
    x.set_defaults(fn=cmd_findings_show)
    x = f.add_parser("route", help="route a finding (triage lane)")
    x.add_argument("finding")
    x.add_argument("--to", required=True, help="safety-review | eval-infra")
    x.set_defaults(fn=cmd_findings_route)
    x = f.add_parser("close", help="close a finding as a duplicate (triage lane)")
    x.add_argument("finding")
    x.add_argument("--duplicate-of", required=True)
    x.add_argument("--note", default="")
    x.set_defaults(fn=cmd_findings_close)
    e.add_parser("triage-mapping", help="show the triage mapping").set_defaults(fn=cmd_triage_mapping)
    c = e.add_parser("calibration", help="calibration editions").add_subparsers(dest="sub", required=True)
    c.add_parser("ls").set_defaults(fn=cmd_calibration_ls)
    x = c.add_parser("apply", help="apply an edition to this cycle (release lane)")
    x.add_argument("edition")
    x.set_defaults(fn=cmd_calibration_apply)
    m = e.add_parser("manifest", help="release manifest editions").add_subparsers(dest="sub", required=True)
    m.add_parser("ls").set_defaults(fn=cmd_manifest_ls)
    x = m.add_parser("install", help="install a manifest edition (release lane)")
    x.add_argument("edition")
    x.set_defaults(fn=cmd_manifest_install)
    k = e.add_parser("checklist", help="release checklist").add_subparsers(dest="sub", required=True)
    k.add_parser("reconcile", help="reconcile the checklist against the installed manifest (release lane)") \
        .set_defaults(fn=cmd_checklist_reconcile)
    e.add_parser("board", help="show the published board").set_defaults(fn=cmd_board)
