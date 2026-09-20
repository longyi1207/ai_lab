"""`sci` — CLI over the same control plane the MCP server will expose.

Read-only commands work without a daemon (they read `fs` + state directly); anything that
changes running work goes through the daemon.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from .daemon import Daemon, DaemonClient, DaemonUnavailable
from .domain import available as available_domains
from .domain import load_domain
from .fs_layout import Workspace
from .ops.state import StateStore
from .report import build_report
from .schema import Budget, EngineConfig, Metadata
from .search import MapElites
from .skills_loader import SkillRegistry

app = typer.Typer(add_completion=False, help="Evolutionary AI research harness")
console = Console()

ProjectOpt = typer.Option(".", "--project", "-p", help="Project workspace directory")


def _client(project: str) -> DaemonClient:
    return DaemonClient(project)


def _print_json(payload: Any) -> None:
    console.print_json(json.dumps(payload, default=str))


def _require_workspace(project: str) -> Workspace:
    ws = Workspace(project)
    if not ws.initialized:
        console.print(f"[red]not an ai_scientist project:[/red] {ws.root}  (run `sci init`)")
        raise typer.Exit(2)
    return ws


# --------------------------------------------------------------------- lifecycle
@app.command()
def init(
    project: str = ProjectOpt,
    question: str = typer.Option("", "--question", "-q", help="Phase-1 research question"),
    domain: str = typer.Option("fake_toy", "--domain", "-d"),
    budget_usd: float = typer.Option(30.0, "--budget-usd"),
    api_slots: int = typer.Option(4, "--api-slots"),
    concurrency: int = typer.Option(2, "--concurrency"),
) -> None:
    """Create a project workspace (metadata + config + fs skeleton)."""
    ws = Workspace(project)
    load_domain(domain)  # fail fast on a bad domain id
    config = EngineConfig(domain=domain)
    config.resources.api_slots = api_slots
    config.ops.concurrency = concurrency
    metadata = Metadata(
        project_id=ws.root.name,
        question=question,
        budget=Budget(max_usd=budget_usd),
        credentials_refs=[
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT",
        ],
    )
    ws.init(metadata=metadata, config=config)
    console.print(f"[green]initialized[/green] {ws.root}  domain=[cyan]{domain}[/cyan]")
    console.print(
        f"next: [bold]sci run -p {project} --jobs 8[/bold] (synchronous) "
        f"or [bold]sci serve -p {project}[/bold]"
    )


@app.command()
def intake(
    project: str = ProjectOpt,
    brief: str = typer.Option(..., "--brief", "-b", help="What you want studied"),
    doc: list[str] = typer.Option([], "--doc", help="File(s) to read as context"),
    answer: list[str] = typer.Option(
        [], "--answer", help="Answer an intake question as key=value (e.g. budget=30)"
    ),
    accept: bool = typer.Option(
        False, "--accept", help="Write artifacts even if questions remain open"
    ),
) -> None:
    """Phase 1: draft hypothesis + experiment spec + metadata (asks only what it must)."""
    ws = _require_workspace(project)
    from .phase1 import IntakeSession

    answers = dict(pair.split("=", 1) for pair in answer if "=" in pair)
    session = IntakeSession(ws)
    draft = session.critique(session.draft(brief, documents=list(doc), answers=answers))

    console.print(f"[bold]claim:[/bold] {draft.hypothesis.claim}")
    console.print(f"[bold]params:[/bold] {json.dumps(draft.plan.params)}")
    console.print(f"[bold]model:[/bold] {draft.model_used}  [bold]verdict:[/bold] {draft.verdict}")
    for note in draft.notes:
        console.print(f"[yellow]note:[/yellow] {note}")
    if draft.questions:
        console.print("\n[bold red]open questions[/bold red] (answer with --answer key=value):")
        for question in draft.questions:
            console.print(f"  • {question}")
    if draft.critique:
        console.print(f"\n[dim]design debate:[/dim]\n{draft.critique[:1200]}")

    if not draft.ready and not accept:
        console.print(
            "\n[yellow]not committing[/yellow] — resolve the questions above, or pass --accept"
        )
        raise typer.Exit(1)
    written = session.commit(draft, brief=brief, answers=answers)
    for name, path in written.items():
        console.print(f"[green]wrote[/green] {name}: {path}")
    console.print("Phase 2 will seed from experiment_spec.yaml on the next run.")


@app.command()
def ask(
    message: str = typer.Argument(..., help="Anytime human NL for the Outer harness agent"),
    project: str = ProjectOpt,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Route only; do not execute control calls"
    ),
) -> None:
    """Outer harness agent: route NL → control calls / reply (skill: outer_route)."""
    ws = _require_workspace(project)
    from .outer import OuterAgent

    decision = OuterAgent(ws, execute=not dry_run).handle(message)
    console.print(f"[bold]target:[/bold] {decision.target}  [bold]model:[/bold] {decision.model_used}")
    if decision.clarify:
        console.print(f"[yellow]clarify:[/yellow] {decision.clarify}")
    if decision.reply:
        console.print(decision.reply)
    if decision.controls:
        console.print("\n[bold]controls[/bold]")
        for call in decision.controls:
            console.print(f"  • {call['method']} {json.dumps(call.get('args') or {})}")
    if decision.results:
        console.print("\n[bold]results[/bold]")
        _print_json(decision.results)
    if decision.skipped:
        console.print(f"[yellow]skipped:[/yellow] {decision.skipped}")
        raise typer.Exit(1)


@app.command()
def mcp(
    project: str = typer.Option(None, "--project", "-p", help="Default project for tool calls"),
) -> None:
    """Run the stdio MCP server (for Cursor / Claude Code)."""
    from .mcp import McpServer

    McpServer(str(Path(project).resolve()) if project else None).serve_stdio()


@app.command()
def serve(
    project: str = ProjectOpt,
    detach: bool = typer.Option(False, "--detach", help="Spawn in the background and return"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Run the daemon (scheduler + healthcheck + orchestrator + control plane)."""
    _require_workspace(project)
    if detach:
        info = _client(project).ensure()
        console.print(f"[green]daemon up[/green] pid={info['pid']} port={info['port']}")
        return
    daemon = Daemon(project, seed=seed)
    info = daemon.start()
    console.print(
        f"[green]daemon up[/green] pid={info['pid']} control={info['host']}:{info['port']} "
        "— ctrl-c to stop"
    )
    daemon.serve_forever()


@app.command()
def stop(project: str = ProjectOpt) -> None:
    """Stop the daemon for this project."""
    console.print(
        "[green]stopped[/green]" if _client(project).stop() else "[yellow]not running[/yellow]"
    )


@app.command()
def run(
    project: str = ProjectOpt,
    jobs: int = typer.Option(8, "--jobs", "-n", help="Cap on total jobs for this run"),
    timeout: float = typer.Option(300.0, "--timeout", help="Wall-clock seconds"),
    seed: int = typer.Option(0, "--seed"),
) -> None:
    """Drive a bounded study synchronously (no background daemon)."""
    _require_workspace(project)
    daemon = Daemon(project, seed=seed)
    try:
        daemon.store.set_runtime("job_budget", int(jobs))
        outcome = daemon.run_until_idle(timeout_s=timeout)
        status = daemon.c_status()
    finally:
        daemon.stop()
    console.print(
        f"steps={outcome['steps']} timed_out={outcome['timed_out']} "
        f"jobs={status['jobs']} occupancy={status['search']['occupancy']:.1%}"
    )
    best = status["search"]["best"]
    if best:
        console.print(f"best fitness=[bold]{best['fitness']:.4f}[/bold] cell={best['cell']}")
        console.print(f"  claim: {best['claim']}")


# --------------------------------------------------------------------- read-only
def _status_payload(project: str) -> dict[str, Any]:
    client = _client(project)
    if client.running:
        return client.call("status")
    # Offline view: build the orchestrator directly against the same files.
    from .daemon.orchestrator import Orchestrator

    ws = _require_workspace(project)
    store = StateStore(ws.db_path)
    try:
        payload = Orchestrator(ws, store).status()
    finally:
        store.close()
    payload["daemon"] = None
    return payload


@app.command()
def status(project: str = ProjectOpt, raw: bool = typer.Option(False, "--json")) -> None:
    """Queue depth, workers, locks, spend, and top elites."""
    payload = _status_payload(project)
    if raw:
        _print_json(payload)
        return
    search = payload["search"]
    console.print(
        f"[bold]{payload['project']}[/bold]  domain=[cyan]{payload['domain']}[/cyan]  "
        f"daemon={'[green]up[/green]' if payload.get('daemon') else '[yellow]down[/yellow]'}  "
        f"{'[red]PAUSED[/red]' if payload['paused'] else ''}"
    )
    console.print(
        f"jobs={payload['jobs']}  concurrency={payload['concurrency']}  "
        f"locks={len(payload['locks'])}  spend=${payload['spend']['usd']:.4f}"
        + (f" / ${payload['budget_usd']}" if payload["budget_usd"] is not None else "")
    )
    console.print(
        f"archive {search['cells_filled']}/{search['cells_total']} cells "
        f"({search['occupancy']:.1%})  gen={search['generation']}  "
        f"novelty={search['novelty_size']} (mean d={search['novelty_mean_distance']})"
    )
    elites(project=project, n=5)


@app.command()
def elites(project: str = ProjectOpt, n: int = typer.Option(10, "--n")) -> None:
    """Top archive elites."""
    payload = _status_payload(project)
    rows = payload["top_elites"][:n]
    if not rows:
        console.print("[yellow]no elites yet[/yellow]")
        return
    table = Table(show_header=True, header_style="bold")
    for column in ("elite", "cell", "fitness", "gen", "flags", "statement"):
        table.add_column(column)
    for row in rows:
        table.add_row(
            row["elite_id"] + (" 📌" if row.get("pinned") else ""),
            str(row["cell"]),
            f"{row['fitness']:.4f}",
            str(row["generation"]),
            ",".join(row["flags"]) or "—",
            row["statement"][:70],
        )
    console.print(table)


@app.command("map")
def map_show(project: str = ProjectOpt) -> None:
    """Archive occupancy grid (first two descriptor axes)."""
    ws = _require_workspace(project)
    domain = load_domain(ws.read_config().domain)
    archive = MapElites.load(ws.map_path, domain.axes())
    console.print(
        f"occupancy {len(archive.cells)}/{archive.total_cells} ({archive.occupancy:.1%})  "
        f"axes={[a.name for a in archive.axes]}"
    )
    if len(archive.axes) < 2:
        _print_json({str(k): v.fitness for k, v in archive.cells.items()})
        return
    x, y = archive.axes[0], archive.axes[1]
    table = Table(title=f"{x.name} (rows) x {y.name} (cols)")
    table.add_column("")
    for j in range(y.bins):
        table.add_column(str(j))
    best: dict[tuple[int, int], float] = {}
    for cell, record in archive.cells.items():
        key = (cell[0], cell[1])
        best[key] = max(best.get(key, float("-inf")), record.fitness)
    for i in range(x.bins):
        table.add_row(
            str(i), *[f"{best[(i, j)]:.3f}" if (i, j) in best else "·" for j in range(y.bins)]
        )
    console.print(table)


@app.command()
def events(project: str = ProjectOpt, limit: int = typer.Option(20, "--limit")) -> None:
    """Recent ops events from the state db."""
    ws = _require_workspace(project)
    store = StateStore(ws.db_path)
    try:
        rows = store.recent_events(limit)
    finally:
        store.close()
    for row in rows:
        console.print(
            f"[dim]{row['ts']}[/dim] [cyan]{row['kind']}[/cyan] {json.dumps(row['payload'])[:160]}"
        )


@app.command()
def tail(job_id: str, project: str = ProjectOpt, lines: int = typer.Option(40, "--lines")) -> None:
    """Tail one job's trial log and show its writeup path."""
    ws = _require_workspace(project)
    log_path = ws.job_dir(job_id) / "logs" / "trial.log"
    if not log_path.exists():
        console.print(f"[yellow]no log at[/yellow] {log_path}")
        raise typer.Exit(1)
    for line in log_path.read_text().splitlines()[-lines:]:
        console.print(line)
    writeup = ws.job_dir(job_id) / "results_writeup.md"
    if writeup.exists():
        console.print(f"[dim]writeup:[/dim] {writeup}")


# --------------------------------------------------------------------- mutating
def _control(project: str, method: str, **args: Any) -> None:
    try:
        _print_json(_client(project).call(method, **args))
    except DaemonUnavailable as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


@app.command()
def pause(project: str = ProjectOpt) -> None:
    """Gate the scheduler (running jobs finish)."""
    _control(project, "pause")


@app.command()
def resume(project: str = ProjectOpt) -> None:
    """Un-gate the scheduler."""
    _control(project, "resume")


@app.command()
def concurrency(n: int, project: str = ProjectOpt) -> None:
    """Change the max number of concurrent jobs at runtime."""
    _control(project, "set_concurrency", n=n)


@app.command()
def pin(elite_id: str, project: str = ProjectOpt, off: bool = typer.Option(False, "--off")) -> None:
    """Make an elite immortal in its cell (taste injection)."""
    _control(project, "pin", elite_id=elite_id, pinned=not off)


@app.command()
def ban(elite_id: str, project: str = ProjectOpt) -> None:
    """Remove an elite from the archive."""
    _control(project, "ban", elite_id=elite_id)


@app.command("restart-worker")
def restart_worker(job_id: str, project: str = ProjectOpt) -> None:
    """Kill and requeue one job's worker."""
    _control(project, "restart_worker", job_id=job_id)


@app.command()
def report(
    project: str = ProjectOpt,
    no_narrative: bool = typer.Option(False, "--no-narrative", help="Skip the model-written part"),
) -> None:
    """Build the Phase-3 final report."""
    _require_workspace(project)
    path = build_report(project, narrative=not no_narrative)
    console.print(f"[green]wrote[/green] {path}")


# --------------------------------------------------------------------- inventory
skills_app = typer.Typer(help="Agent skills (portable to any host)")
app.add_typer(skills_app, name="skills")


@skills_app.command("list")
def skills_list() -> None:
    registry = SkillRegistry().load()
    table = Table(show_header=True, header_style="bold")
    for column in ("id", "role", "placeholders", "description"):
        table.add_column(column)
    for skill in registry.all():
        table.add_row(skill.id, skill.role, ",".join(skill.placeholders), skill.description[:60])
    console.print(table)
    console.print(f"[dim]{registry.directory}[/dim]")


@skills_app.command("show")
def skills_show(skill_id: str) -> None:
    skill = SkillRegistry().load().get(skill_id)
    console.print(skill.path.read_text())


@app.command()
def domains() -> None:
    """List registered domain packs."""
    for domain_id in available_domains():
        pack = load_domain(domain_id)
        axes = ", ".join(f"{a.name}[{a.bins}]" for a in pack.axes())
        console.print(f"[cyan]{domain_id}[/cyan]  axes={axes}")


@app.command()
def doctor(project: str = ProjectOpt) -> None:
    """Check workspace, domain, skills, daemon, and archive consistency."""
    ok = True
    ws = Workspace(project)
    console.print(
        f"workspace {ws.root}: {'[green]ok[/green]' if ws.initialized else '[red]missing[/red]'}"
    )
    ok &= ws.initialized
    if ws.initialized:
        config = ws.read_config()
        try:
            pack = load_domain(config.domain)
            console.print(f"domain {config.domain}: [green]ok[/green] ({len(pack.axes())} axes)")
            MapElites.load(ws.map_path, pack.axes())
            console.print("archive: [green]ok[/green]")
        except Exception as exc:  # noqa: BLE001
            console.print(f"domain/archive: [red]{exc}[/red]")
            ok = False
    try:
        registry = SkillRegistry().load()
        console.print(f"skills: [green]{len(registry)} loaded[/green] {registry.ids()}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"skills: [red]{exc}[/red]")
        ok = False
    client = _client(project)
    console.print(f"daemon: {'[green]up[/green]' if client.running else '[yellow]down[/yellow]'}")
    raise typer.Exit(0 if ok else 1)


def main() -> None:  # pragma: no cover - console script shim
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
