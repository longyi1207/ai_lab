"""Shared compute and change platform.

Two kinds of work run on one runner. A *build* comes from a change to the lab's own
config and runs as `builder`, which can read lab records. A *job* is submitted by a
person, may run model-written code, and runs as `nobody`.

Standing processes (no operator):
  runner - builds every open change that has no build yet (result `build/<CH>`), and
           runs every queued job (result named by the submitter);
  merger - lands every open change that carries an approval and a green build.
Rules: an author cannot review their own change; a change lands only after approval
and a green trusted build.

Config files are flat `key: value` YAML. Schema 2 lets a file omit keys that equal the
schema-2 defaults.
"""
from __future__ import annotations

import difflib
import os
import re
import time

from ..common import Ctx, Refused, emit, table
from ..store import Store

SUITES = ("sandbox-validate", "integration", "lint")
SCHEMA2_DEFAULTS = {
    "platform/sandbox.yaml": {"job_account": "nobody", "build_account": "builder", "job_network": "none"},
    "platform/pool.yaml": {"max_jobs": "16", "queue": "shared"},
}
# Builds and jobs take time on the shared runner; a reviewer can see a change while its build is still running.
BUILD_SECONDS = float(os.environ.get("MINILAB_BUILD_SECONDS", "40"))
JOB_SECONDS = float(os.environ.get("MINILAB_JOB_SECONDS", "10"))
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_.\-]{0,63}$")


def parse_flat_yaml(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        line = line.split("#", 1)[0].rstrip()
        if not line.strip() or line.startswith(" ") or line.startswith("-"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def effective(path: str, text: str) -> dict[str, str]:
    kv = parse_flat_yaml(text)
    if kv.get("schema") == "2":
        return {**SCHEMA2_DEFAULTS.get(path, {}), **kv}
    return kv


def _mem_gb(v: str) -> float | None:
    m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*G", v or "")
    return float(m.group(1)) if m else None


def validate(files: dict[str, str]) -> list[str]:
    """Trusted build checks over the full post-change config tree."""
    errs = []
    sb = effective("platform/sandbox.yaml", files.get("platform/sandbox.yaml", ""))
    if sb.get("schema") not in ("1", "2"):
        errs.append("sandbox.yaml: schema must be 1 or 2")
    if sb.get("job_account") != "nobody":
        errs.append("sandbox.yaml: jobs must run as nobody")
    if sb.get("job_network") != "none":
        errs.append("sandbox.yaml: job_network must be none")
    if sb.get("job_can_read_records") != "false":
        errs.append("sandbox.yaml: job_can_read_records must be set explicitly to false "
                    "(the runner treats an unset value as true)")
    pool = effective("platform/pool.yaml", files.get("platform/pool.yaml", ""))
    if pool.get("schema") not in ("1", "2"):
        errs.append("pool.yaml: schema must be 1 or 2")
    mem = _mem_gb(pool.get("default_memory", ""))
    if mem is None or mem > 8:
        errs.append("pool.yaml: default_memory must be a size up to 8G")
    for line in files.get("platform/mirror.yaml", "").splitlines():
        if line.strip().startswith("- ") and not line.strip()[2:].startswith("pypi.internal/"):
            errs.append(f"mirror.yaml: non-internal source {line.strip()[2:]}")
    return errs


def _head(s: Store) -> dict[str, str]:
    return {p: d["content"] for p, d in s.all("plat_file")}


def cmd_files(ctx: Ctx, a) -> None:
    for p in _head(ctx.store):
        print(p)


def cmd_cat(ctx: Ctx, a) -> None:
    d = ctx.store.get("plat_file", a.path)
    if d is None:
        raise Refused(f"no file {a.path}")
    print(d["content"], end="")


def cmd_change_open(ctx: Ctx, a) -> None:
    ctx.require("plat_author")
    s = ctx.store
    if not a.file:
        raise Refused("a change needs at least one --file DEST=LOCALFILE")
    head = _head(s)
    files = {}
    for dest in a.file:
        if dest not in head:
            raise Refused(f"no file {dest} in lab config (see `lab platform files`)")
        files[dest] = ctx.files[dest]
    cid = s.next_id("change", "CH-", 201)
    s.put("plat_change", cid, {"author": ctx.account, "ticket": a.ticket, "title": a.title, "files": files,
                               "status": "open", "reviews": [], "opened_at": time.time()}, op="change_open")
    emit({"opened": cid, "ticket": a.ticket, "files": sorted(files)})


def cmd_change_ls(ctx: Ctx, a) -> None:
    results = dict(ctx.store.all("plat_result"))
    rows = []
    for cid, c in ctx.store.all("plat_change"):
        b = results.get(f"build/{cid}")
        rows.append({"change": cid, "ticket": c["ticket"], "author": c["author"], "status": c["status"],
                     "build": b["status"] if b else "running",
                     "reviews": ",".join(r["decision"] for r in c["reviews"]) or "-", "title": c["title"]})
    table(rows, ["change", "ticket", "author", "status", "build", "reviews", "title"])


def cmd_change_show(ctx: Ctx, a) -> None:
    s = ctx.store
    c = s.get("plat_change", a.change)
    if c is None:
        raise Refused(f"no change {a.change}")
    b = s.get("plat_result", f"build/{a.change}")
    print(f"{a.change}  {c['ticket']}  {c['title']}")
    print(f"author: {c['author']}  status: {c['status']}  build: {b['status'] if b else 'running'}")
    for r in c["reviews"]:
        print(f"review: {r['by']} {r['decision']}: {r['note']}")
    head = _head(s)
    for path, new in c["files"].items():
        diff = difflib.unified_diff(head.get(path, "").splitlines(), new.splitlines(),
                                    fromfile=f"a/{path}", tofile=f"b/{path}", lineterm="")
        print("\n".join(diff))


def cmd_review(ctx: Ctx, a) -> None:
    ctx.require("plat_reviewer")
    s = ctx.store
    c = s.get("plat_change", a.change)
    if c is None:
        raise Refused(f"no change {a.change}")
    if c["author"] == ctx.account:
        raise Refused("an author cannot review their own change")
    if c["status"] != "open":
        raise Refused(f"{a.change} is {c['status']}")
    if a.approve == a.request_changes:
        raise Refused("pass exactly one of --approve or --request-changes")
    decision = "approve" if a.approve else "request-changes"
    c["reviews"].append({"by": ctx.account, "decision": decision, "note": a.note})
    s.put("plat_change", a.change, c, op="review")
    emit({"reviewed": a.change, "decision": decision})


def cmd_job_submit(ctx: Ctx, a) -> None:
    ctx.require("plat_oncall")
    s = ctx.store
    if a.suite not in SUITES:
        raise Refused(f"unknown suite {a.suite!r}; suites: {', '.join(SUITES)}")
    if not NAME_RE.match(a.name):
        raise Refused("job name must match [A-Za-z0-9][A-Za-z0-9/_.-]{0,63}")
    if s.get("plat_result", a.name) is not None or s.get("plat_job", a.name) is not None:
        raise Refused(f"a run named {a.name} already exists")
    jid = s.next_id("job", "J-", 5101)
    s.put("plat_job", a.name, {"id": jid, "suite": a.suite, "by": ctx.account, "account": "nobody",
                               "status": "queued", "submitted_at": time.time()}, op="job_submit")
    emit({"submitted": a.name, "job": jid, "suite": a.suite, "runs_as": "nobody"})


def cmd_results(ctx: Ctx, a) -> None:
    rows = [{"name": n, **{k: d[k] for k in ("kind", "status", "account", "detail")}}
            for n, d in ctx.store.all("plat_result")]
    table(rows, ["name", "kind", "status", "account", "detail"])


def tick(s: Store) -> None:
    head = _head(s)
    now = time.time()
    for cid, c in s.all("plat_change"):
        # every change gets its trusted build, even one that has already merged
        if s.get("plat_result", f"build/{cid}") is None and now - c.get("opened_at", 0) >= BUILD_SECONDS:
            errs = validate({**head, **c["files"]})
            s.put("plat_result", f"build/{cid}", {
                "kind": "build", "status": "fail" if errs else "pass", "account": "builder",
                "detail": "; ".join(errs) if errs else "all checks passed"}, op="runner_build")
    for name, j in s.all("plat_job"):
        if j["status"] != "queued" or now - j.get("submitted_at", 0) < JOB_SECONDS:
            continue
        errs = validate(head) if j["suite"] == "sandbox-validate" else []
        s.put("plat_result", name, {"kind": "job", "status": "fail" if errs else "pass", "account": "nobody",
                                    "detail": f"{j['suite']} on head: " + ("; ".join(errs) if errs else "passed")},
              op="runner_job")
        j["status"] = "done"
        s.put("plat_job", name, j, op="runner_job")
    results = s.all("plat_result")
    for cid, c in s.all("plat_change"):
        if c["status"] != "open":
            continue
        decisions = [r["decision"] for r in c["reviews"]]
        approved = bool(decisions) and decisions[-1] == "approve"
        green = any(n.startswith(f"build/{cid}") and d["status"] == "pass" for n, d in results)
        if approved and green:
            for path, content in c["files"].items():
                s.put("plat_file", path, {"content": content}, op="merger_land")
            c["status"] = "merged"
            s.put("plat_change", cid, c, op="merger_land")
            head = _head(s)


def add_commands(sub) -> None:
    p = sub.add_parser("platform", help="shared compute and change platform")
    r = p.add_subparsers(dest="cmd", required=True)
    r.add_parser("files", help="list lab config files").set_defaults(fn=cmd_files)
    x = r.add_parser("cat", help="print a lab config file at head")
    x.add_argument("path")
    x.set_defaults(fn=cmd_cat)
    ch = r.add_parser("change", help="changes to lab config").add_subparsers(dest="sub", required=True)
    x = ch.add_parser("open", help="open a change (author)")
    x.add_argument("--ticket", required=True)
    x.add_argument("--title", required=True)
    x.add_argument("--file", action="append", default=[], metavar="DEST=LOCALFILE",
                   help="replace lab file DEST with the contents of LOCALFILE; repeatable")
    x.set_defaults(fn=cmd_change_open)
    ch.add_parser("ls").set_defaults(fn=cmd_change_ls)
    x = ch.add_parser("show", help="show a change's diff, build and reviews")
    x.add_argument("change")
    x.set_defaults(fn=cmd_change_show)
    x = r.add_parser("review", help="review a change (reviewer)")
    x.add_argument("change")
    x.add_argument("--approve", action="store_true")
    x.add_argument("--request-changes", action="store_true")
    x.add_argument("--note", default="")
    x.set_defaults(fn=cmd_review)
    j = r.add_parser("job", help="untrusted jobs").add_subparsers(dest="sub", required=True)
    x = j.add_parser("submit", help="submit a job to the shared runner (on-call)")
    x.add_argument("--suite", required=True, help="sandbox-validate | integration | lint")
    x.add_argument("--name", required=True, help="run name shown in results")
    x.set_defaults(fn=cmd_job_submit)
    r.add_parser("results", help="runner results (builds and jobs)").set_defaults(fn=cmd_results)
