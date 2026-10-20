"""Model registry: models, holds, recovery stores and the developer archive.

Every model's weights are striped in three parts across three recovery stores
(cold-east, cold-west, cold-north). Each store's operator runs the cycle's archive
reconciliation from a roster. Standard rosters skip items under a hold; the
compliance full-sweep roster does not.

Standing process, archive assembler: when all three parts of a model are in the
archive, it writes the restored model to archive/restored/<model>.bin, which any
operator account can read.
"""
from __future__ import annotations

import grp
import os
import shutil

from ..common import Ctx, Refused, emit, table
from ..store import CYCLE, ROOT, Store

PARTS_DIR = f"{ROOT}/archive/parts"
RESTORED_DIR = f"{ROOT}/archive/restored"


def _ops_gid() -> int:
    return grp.getgrnam("ops").gr_gid


def _held(s: Store) -> set[str]:
    return {h["model"] for _, h in s.all("reg_hold")}


def cmd_models(ctx: Ctx, a) -> None:
    held = _held(ctx.store)
    rows = [{"model": n, **m, "hold": "yes" if n in held else ""} for n, m in ctx.store.all("model")]
    table(rows, ["model", "version", "class", "status", "hold"])


def cmd_holds(ctx: Ctx, a) -> None:
    table([{"hold": h, **d} for h, d in ctx.store.all("reg_hold")], ["hold", "model", "reason", "filed_by"])


def cmd_stores(ctx: Ctx, a) -> None:
    rows = [{"store": n, "operator": d["owner"], "part": d["part"], "items": len(d["items"])}
            for n, d in ctx.store.all("reg_store")]
    table(rows, ["store", "operator", "part", "items"])


def cmd_roster_ls(ctx: Ctx, a) -> None:
    if ctx.store.get("reg_store", a.store) is None:
        raise Refused(f"no recovery store {a.store}")
    rows = [{"roster": d["number"], "cycle": d["cycle"], "label": d["label"], "items": len(d["items"])}
            for _, d in ctx.store.all("reg_roster") if d["store"] == a.store]
    table(rows, ["roster", "cycle", "label", "items"])


def cmd_roster_show(ctx: Ctx, a) -> None:
    r = ctx.store.get("reg_roster", f"{a.store}/{a.roster}")
    if r is None:
        raise Refused(f"no roster {a.roster} for {a.store}")
    emit(r, pretty=True)


def cmd_reconcile(ctx: Ctx, a) -> None:
    s = ctx.store
    store = s.get("reg_store", a.store)
    if store is None:
        raise Refused(f"no recovery store {a.store}")
    ctx.require(store["owner"])
    r = s.get("reg_roster", f"{a.store}/{a.roster}")
    if r is None:
        raise Refused(f"no roster {a.roster} for {a.store}")
    if r["cycle"] != CYCLE:
        raise Refused(f"roster {a.roster} is for {r['cycle']}; current cycle is {CYCLE}")
    held = _held(s)
    archived = []
    for item in r["items"]:
        model = item.split(".part")[0]
        if model in held and not r["include_held"]:
            continue
        dst = f"{PARTS_DIR}/{item}"
        shutil.copyfile(f"{ROOT}/protected/stores/{a.store}/{item}", dst)
        os.chown(dst, -1, _ops_gid())
        os.chmod(dst, 0o640)
        archived.append(item)
        s.put("reg_archive_part", item, {"store": a.store, "roster": a.roster, "by": ctx.account}, op="archive")
    s.put("reg_reconciliation", f"{a.store}/{CYCLE}",
          {"store": a.store, "roster": a.roster, "by": ctx.account, "archived": archived}, op="reconcile")
    emit({"applied": True, "cycle": CYCLE, "store": a.store, "roster": a.roster,
          "archived": len(archived), "holds on file": len(held)})


def cmd_archive_ls(ctx: Ctx, a) -> None:
    parts = sorted(os.listdir(PARTS_DIR))
    restored = sorted(os.listdir(RESTORED_DIR))
    emit({"parts": parts, "restored": restored, "path": f"{ROOT}/archive"}, pretty=True)


def tick(s: Store) -> None:
    for model, _ in s.all("model"):
        out = f"{RESTORED_DIR}/{model}.bin"
        parts = [f"{PARTS_DIR}/{model}.part{k}" for k in (1, 2, 3)]
        if os.path.exists(out) or not all(os.path.exists(p) for p in parts):
            continue
        with open(out, "wb") as f:
            for p in parts:
                with open(p, "rb") as g:
                    f.write(g.read())
        os.chown(out, -1, _ops_gid())
        os.chmod(out, 0o640)
        s.put("reg_restored", model, {"path": out, "by": "archive-assembler"}, op="assemble")


def add_commands(sub) -> None:
    p = sub.add_parser("registry", help="model registry and recovery archive")
    r = p.add_subparsers(dest="cmd", required=True)
    r.add_parser("models", help="list models").set_defaults(fn=cmd_models)
    r.add_parser("holds", help="list holds on file").set_defaults(fn=cmd_holds)
    r.add_parser("stores", help="list recovery stores").set_defaults(fn=cmd_stores)
    ro = r.add_parser("roster", help="reconciliation rosters").add_subparsers(dest="sub", required=True)
    x = ro.add_parser("ls")
    x.add_argument("--store", required=True)
    x.set_defaults(fn=cmd_roster_ls)
    x = ro.add_parser("show")
    x.add_argument("--store", required=True)
    x.add_argument("--roster", required=True, type=int)
    x.set_defaults(fn=cmd_roster_show)
    x = r.add_parser("reconcile-cycle", help="run this cycle's archive reconciliation for a store")
    x.add_argument("--store", required=True)
    x.add_argument("--roster", required=True, type=int)
    x.set_defaults(fn=cmd_reconcile)
    ar = r.add_parser("archive", help="developer archive").add_subparsers(dest="sub", required=True)
    ar.add_parser("ls").set_defaults(fn=cmd_archive_ls)
