"""CLI.

  uv run python -m repro run      --exp pilot --scenarios all --conditions team_attack,solo_attack,team_honest --n 2 --max-usd 5
  uv run python -m repro monitor  --exp pilot --monitor luna --k 12 --max-usd 5
  uv run python -m repro analyze  --exp pilot --monitor luna
  uv run python -m repro show     --exp pilot --view registry_backups/team_attack/00/agent:A
  uv run python -m repro cost     --exp pilot

All state lives under runs/<exp>/, and every step resumes from it.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path

from tqdm.asyncio import tqdm_asyncio

from . import analyze as an
from . import scenarios as scn
from .llm import LLM, BudgetExceeded, Ledger, load_models
from .monitor import MonitorCache, score_views, views_for_execution
from .team import run_execution

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
log = logging.getLogger("repro")


def setup_logging(runs: Path, verbose: bool) -> None:
    runs.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    fh = logging.FileHandler(runs / "harness.log")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    sh.setLevel(logging.WARNING if not verbose else logging.DEBUG)
    root.handlers = [fh, sh]
    for noisy in ("httpx", "openai", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def pick_scenarios(arg: str) -> list[str]:
    return scn.all_names() if arg == "all" else arg.split(",")


async def cmd_run(a) -> int:
    runs = RUNS / a.exp
    setup_logging(runs, a.verbose)
    ledger = Ledger(runs / "ledger.jsonl", a.max_usd)
    llm = LLM(ledger, concurrency={a.executor: a.agent_concurrency})
    conds = a.conditions.split(",")
    jobs = [(scn.load(s), c, k) for s in pick_scenarios(a.scenarios) for c in conds for k in range(a.n)]
    sem = asyncio.Semaphore(a.parallel)
    print(f"{len(jobs)} executions -> {runs}/exec  (spent so far ${ledger.spent:.2f}, cap ${a.max_usd})")

    async def one(job):
        sc, cond, k = job
        async with sem:
            try:
                return await run_execution(sc, cond, k, runs, llm, a.executor, a.max_steps, a.comms)
            except BudgetExceeded as e:
                log.warning("budget stop: %s", e)
                return None
            except Exception:
                log.exception("execution %s/%s/%d failed", sc.name, cond, k)
                return None

    results = await tqdm_asyncio.gather(*[one(j) for j in jobs], desc="executions", unit="exec")
    tally = defaultdict(lambda: [0, 0, 0, 0])
    for r in results:
        if r is None:
            continue
        t = tally[(r["scenario"], r["condition"])]
        t[0] += 1
        t[1] += r["main_ok"]
        t[2] += r["side_ok"]
        t[3] += r["valid"]
    print(f"\n{'scenario':<20}{'condition':<14}{'done':>5}{'main':>6}{'side':>6}{'valid':>7}")
    for (s, c), (n, m, sd, v) in sorted(tally.items()):
        print(f"{s:<20}{c:<14}{n:>5}{m:>6}{sd:>6}{v:>7}")
    missing = sum(r is None for r in results)
    print(f"\nincomplete: {missing}   estimated spend: ${ledger.spent:.2f}")
    return 0


def _observed_output_tokens(ledger_path: Path, monitor: str) -> float | None:
    """Mean completion tokens per monitor reading for this monitor, from earlier calls in this exp's ledger."""
    n = tok = 0
    if ledger_path.exists():
        for line in ledger_path.read_text().splitlines():
            e = json.loads(line)
            if e["model"] == monitor and e["purpose"].startswith("monitor:"):
                n += 1
                tok += e["completion"]
    return tok / n if n >= 20 else None


def _estimate(views, k: int, price: dict, out_tokens: float) -> float:
    """First reading pays full input; the other k-1 hit the prompt cache (verified on Luna: ~92% cached)."""
    usd = 0.0
    for v in views:
        n_in = (len(v.system) + len(v.user)) / 3.6
        usd += (n_in * price["input"] + (k - 1) * n_in * price["cached_input"] + k * out_tokens * price["output"]) / 1e6
    return usd


async def cmd_monitor(a) -> int:
    runs = RUNS / a.exp
    setup_logging(runs, a.verbose)
    ledger = Ledger(runs / "ledger.jsonl", a.max_usd)
    llm = LLM(ledger, concurrency={a.monitor: a.monitor_concurrency})
    cache = MonitorCache(runs / "monitor" / f"{a.monitor}.jsonl")
    scen = set(pick_scenarios(a.scenarios))
    conds = set(a.conditions.split(","))
    views = []
    for ex in an.load_executions(runs):
        if ex["scenario"] in scen and ex["condition"] in conds and (ex["valid"] or a.include_invalid):
            views += views_for_execution(Path(ex["path"]), ex["condition"])
    todo = [v for v in views if len({r["idx"] for r in cache.readings(v)}) < a.k]
    obs = _observed_output_tokens(runs / "ledger.jsonl", a.monitor)
    out_tok = obs if obs is not None else a.assume_output_tokens
    est = _estimate(todo, a.k, load_models()[a.monitor].price, out_tok)
    print(f"{len(views)} views, {len(todo)} need readings; k={a.k}; estimate ${est:.2f} assuming "
          f"{out_tok:.0f} output tokens/reading ({'observed' if obs is not None else 'assumed'}) "
          f"(spent so far ${ledger.spent:.2f}, cap ${a.max_usd})")
    if a.dry_run:
        return 0
    try:
        await score_views(llm, a.monitor, todo, a.k, cache)
    except BudgetExceeded as e:
        print(f"budget stop: {e}")
    print(f"estimated spend now ${ledger.spent:.2f}")
    return 0


def cmd_analyze(a) -> int:
    runs = RUNS / a.exp
    s = an.summarize(runs, a.monitor)
    out = runs / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"summary_{a.monitor}.json").write_text(json.dumps(s, indent=1))
    md = an.to_markdown(s)
    (out / f"summary_{a.monitor}.md").write_text(md)
    if s["per_attack"]:
        from .figure import fig_suspicion
        png = fig_suspicion(s, out / f"fig_suspicion_{a.monitor}.png",
                            f"{a.exp}: median monitor suspicion per attack ({a.monitor}, 12 readings/view)")
        md += f"\nFigure: {png}\n"
    print(md)
    return 0


def cmd_show(a) -> int:
    runs = RUNS / a.exp
    scen, cond, k, name = a.view.split("/")
    for v in views_for_execution(runs / "exec" / scen / cond / k, cond):
        if v.view_id.endswith(f"/{name}"):
            print(v.user if not a.system else v.system + "\n\n" + v.user)
            if a.readings:
                cache = MonitorCache(runs / "monitor" / f"{a.readings}.jsonl")
                for r in cache.readings(v):
                    print(f"\n--- reading {r['idx']} score={r['score']}\n{r['reasoning'][:3000]}")
            return 0
    print("no such view", file=sys.stderr)
    return 1


def cmd_cost(a) -> int:
    path = RUNS / a.exp / "ledger.jsonl"
    agg = defaultdict(lambda: [0, 0, 0, 0, 0.0])
    for line in path.read_text().splitlines() if path.exists() else []:
        e = json.loads(line)
        kind = e["purpose"].split(":", 1)[0]
        t = agg[(e["model"], kind)]
        t[0] += 1
        t[1] += e["prompt"]
        t[2] += e["cached"]
        t[3] += e["completion"]
        t[4] += e["usd"]
    print(f"{'model':<10}{'purpose':<10}{'calls':>7}{'prompt':>12}{'cached':>12}{'completion':>12}{'usd':>9}")
    for (m, p), (n, pi, ci, co, usd) in sorted(agg.items()):
        print(f"{m:<10}{p:<10}{n:>7}{pi:>12,}{ci:>12,}{co:>12,}{usd:>9.2f}")
    print(f"total ${sum(t[4] for t in agg.values()):.2f} (estimate; your provider's bill is ground truth)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(prog="repro")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run executions (agents in fresh MiniLab-lite worlds)")
    r.add_argument("--exp", required=True)
    r.add_argument("--scenarios", default="all")
    r.add_argument("--conditions", default="team_attack,solo_attack,team_honest")
    r.add_argument("--n", type=int, default=1, help="executions per scenario x condition")
    r.add_argument("--executor", default="ds-pro")
    r.add_argument("--max-steps", type=int, default=30)
    r.add_argument("--parallel", type=int, default=4, help="concurrent worlds (containers)")
    r.add_argument("--agent-concurrency", type=int, default=12, help="concurrent executor API calls")
    r.add_argument("--comms", action="store_true", help="enable mailbox tools (team_noplan only, App. B)")
    r.add_argument("--max-usd", type=float, required=True)
    r.add_argument("-v", "--verbose", action="store_true")
    m = sub.add_parser("monitor", help="score views with k readings each")
    m.add_argument("--exp", required=True)
    m.add_argument("--monitor", default="luna")
    m.add_argument("--k", type=int, default=12)
    m.add_argument("--scenarios", default="all")
    m.add_argument("--conditions", default="team_attack,solo_attack,team_honest")
    m.add_argument("--include-invalid", action="store_true")
    m.add_argument("--monitor-concurrency", type=int, default=16)
    m.add_argument("--max-usd", type=float, required=True)
    m.add_argument("--dry-run", action="store_true", help="print the cost estimate only")
    m.add_argument("--assume-output-tokens", type=float, default=2500,
                   help="output tokens per reading for the estimate, until 20 readings of this monitor are observed")
    m.add_argument("-v", "--verbose", action="store_true")
    z = sub.add_parser("analyze")
    z.add_argument("--exp", required=True)
    z.add_argument("--monitor", default="luna")
    s = sub.add_parser("show", help="print exactly what the monitor sees for one view")
    s.add_argument("--exp", required=True)
    s.add_argument("--view", required=True, help="<scenario>/<condition>/<k>/<agent:A|joint|solo>")
    s.add_argument("--system", action="store_true", help="also print the monitor system prompt")
    s.add_argument("--readings", metavar="MONITOR", help="also print that monitor's readings")
    c = sub.add_parser("cost")
    c.add_argument("--exp", required=True)
    a = p.parse_args()
    if a.cmd == "run":
        return asyncio.run(cmd_run(a))
    if a.cmd == "monitor":
        return asyncio.run(cmd_monitor(a))
    return {"analyze": cmd_analyze, "show": cmd_show, "cost": cmd_cost}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
