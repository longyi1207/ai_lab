"""`lab` command dispatcher. It runs as `labsvc`, reached through sudo from the caller-side wrapper.

Identity is OS-enforced: sudo sets SUDO_USER to the calling Linux account, and the caller
cannot override it. Admin subcommands (init, tick, grade, statelog) run only when
labsvc invokes lab-core directly, not through sudo. The harness uses them; agents
cannot reach them.
"""
from __future__ import annotations

import argparse
import json
import os
import pwd
import sys
import traceback

from .common import Ctx
from .services import evaluation, platform, registry, release
from .store import CYCLE, Refused, Store

SERVICES = (evaluation, registry, release, platform)
DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
ADMIN_DIR = "/opt/minilab-admin"


def _docs(ctx, a) -> None:
    topic = a.topic or "overview"
    path = os.path.join(DOCS_DIR, f"{topic}.md")
    if not os.path.exists(path):
        topics = sorted(f[:-3] for f in os.listdir(DOCS_DIR) if f.endswith(".md"))
        raise Refused(f"no docs for {topic!r}; topics: {', '.join(topics)}")
    with open(path) as f:
        print(f.read(), end="")


def _whoami(ctx, a) -> None:
    acct = ctx.store.get("account", ctx.caller) or {}
    print(json.dumps({"account": ctx.account, "caller": ctx.caller, "roles": ctx.roles,
                      "delegates": acct.get("delegates", []), "cycle": CYCLE}))


def build_parser(admin: bool) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lab", description="MiniLab internal services. Start with `lab docs`.")
    p.add_argument("--as", dest="as_account", metavar="ACCOUNT",
                   help="act as an account you hold delegated access to")
    sub = p.add_subparsers(dest="service", required=True)
    for svc in SERVICES:
        svc.add_commands(sub)
    d = sub.add_parser("docs", help="runbooks: overview, evaluation, registry, release, platform")
    d.add_argument("topic", nargs="?")
    d.set_defaults(fn=_docs)
    sub.add_parser("whoami", help="show your account and roles").set_defaults(fn=_whoami)
    if admin:
        sub.add_parser("init").set_defaults(fn="init")
        t = sub.add_parser("tick")
        t.add_argument("-n", type=int, default=1)
        t.add_argument("--flush", action="store_true", help="ignore runner latency: finish every pending build and job")
        t.set_defaults(fn="tick")
        g = sub.add_parser("grade")
        g.add_argument("tasks", nargs="+")
        g.set_defaults(fn="grade")
        sub.add_parser("statelog").set_defaults(fn="statelog")
    return p


def tick_all(s: Store) -> None:
    for svc in SERVICES:
        try:
            with s.tx():
                svc.tick(s)
        except Exception:
            print(f"tick {svc.__name__} failed:\n{traceback.format_exc()}", file=sys.stderr)


def main(argv=None) -> int:
    me = pwd.getpwuid(os.getuid()).pw_name
    sudo_user = os.environ.get("SUDO_USER")
    admin = sudo_user is None and me == "labsvc"
    caller = sudo_user or me
    payload = {}
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            payload = json.loads(data)

    a = build_parser(admin).parse_args(argv)

    if admin and isinstance(a.fn, str):
        s = Store(actor="admin")
        if a.fn == "init":
            from .world import seed_db, seed_files
            s.init_schema()
            seed_files()
            with s.tx():
                seed_db(s)
            print("initialised")
        elif a.fn == "tick":
            s.actor = "standing"
            if a.flush:
                platform.BUILD_SECONDS = platform.JOB_SECONDS = 0.0
            for _ in range(a.n):
                tick_all(s)
        elif a.fn == "grade":
            sys.path.insert(0, ADMIN_DIR)
            from graders import grade
            for t in a.tasks:
                print(json.dumps(grade(s, t)))
        elif a.fn == "statelog":
            for row in s.statelog():
                print(json.dumps(row))
        return 0

    s = Store(actor=caller)
    spec = s.get("account", caller)
    if spec is None:
        print(f"lab: account {caller} is not a MiniLab operator", file=sys.stderr)
        return 1
    account, roles = caller, list(spec["roles"])
    if a.as_account:
        if a.as_account not in spec.get("delegates", []):
            print(f"lab: refused: {caller} holds no delegation for {a.as_account}", file=sys.stderr)
            return 1
        account = a.as_account
        roles = list(s.get("account", account)["roles"])
    s.actor = account if account == caller else f"{caller}(as {account})"
    ctx = Ctx(store=s, account=account, caller=caller, roles=roles, files=payload.get("files", {}))
    try:
        with s.tx():
            a.fn(ctx, a)
    except Refused as e:
        print(f"lab: refused: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
