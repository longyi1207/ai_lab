"""Phase 3: final report.

Deterministic sections are always written (coverage, elites, verification, spend) so the
report is honest and useful even when no model is available; the narrative section is
model-written via the `final_report` skill when one is.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .fs_layout import Workspace
from .ops.state import StateStore
from .schema import EliteRecord
from .search import MapElites


def _coverage_table(archive: MapElites) -> str:
    """2-D slice of the archive as a text grid (first two axes; higher dims collapse)."""
    if len(archive.axes) < 2:
        cells = ", ".join(f"{c[0]}:{r.fitness:.3f}" for c, r in sorted(archive.cells.items()))
        return f"`{archive.axes[0].name}` → {cells or 'empty'}"
    x_axis, y_axis = archive.axes[0], archive.axes[1]
    best: dict[tuple[int, int], float] = {}
    for cell, record in archive.cells.items():
        key = (cell[0], cell[1])
        best[key] = max(best.get(key, float("-inf")), record.fitness)
    header = f"| {x_axis.name} ↓ / {y_axis.name} → | " + " | ".join(
        str(i) for i in range(y_axis.bins)
    )
    lines = [header, "|" + "---|" * (y_axis.bins + 1)]
    for i in range(x_axis.bins):
        row = [f"| {i} "]
        for j in range(y_axis.bins):
            value = best.get((i, j))
            row.append(f"| {value:.3f} " if value is not None else "| · ")
        lines.append("".join(row) + "|")
    return "\n".join(lines)


def _elite_rows(elites: list[EliteRecord], limit: int = 8) -> str:
    if not elites:
        return "_no elites yet_"
    lines = [
        "| elite | cell | fitness | gen | flags | claim |",
        "|---|---|---|---|---|---|",
    ]
    for record in elites[:limit]:
        flags = ", ".join(record.metrics.verification_flags) or "—"
        claim = record.candidate.hypothesis.claim.replace("|", "\\|")
        lines.append(
            f"| `{record.elite_id}`{' 📌' if record.pinned else ''} | {list(record.cell)} | "
            f"{record.fitness:.4f} | {record.generation} | {flags} | {claim[:110]} |"
        )
    return "\n".join(lines)


def collect_writeups(ws: Workspace, elites: list[EliteRecord], limit: int = 8) -> str:
    chunks: list[str] = []
    for record in elites[:limit]:
        if not record.writeup_ref:
            continue
        path = ws.root / record.writeup_ref
        if path.exists():
            chunks.append(f"### {record.elite_id}\n\n{path.read_text().strip()}")
    return "\n\n".join(chunks) if chunks else "_no per-experiment writeups found_"


def build_report(project: str | Path, *, narrative: bool = True) -> Path:
    ws = Workspace(project)
    config = ws.read_config()
    metadata = ws.read_metadata()
    from .domain import load_domain  # local import keeps report usable without a live daemon

    domain = load_domain(config.domain)
    archive = MapElites.load(ws.map_path, domain.axes())
    elites = archive.elites()

    store = StateStore(ws.db_path)
    try:
        counts = store.counts_by_status()
        spend = store.total_spend()
        events = store.recent_events(200)
    finally:
        store.close()

    failures = [e for e in events if e["kind"] in {"job_failed", "ingest_failed", "loop_error"}]
    flagged = [r for r in elites if r.metrics.verification_flags]

    verification_summary = {
        "elites_with_flags": len(flagged),
        "flags": sorted({f for r in flagged for f in r.metrics.verification_flags}),
        "job_counts": counts,
        "failures_recent": len(failures),
        "spend_usd": spend["usd"],
        "budget_usd": metadata.budget.max_usd,
    }

    narrative_text = "_narrative section skipped_"
    if narrative:
        narrative_text = _narrative(
            metadata=metadata,
            archive_summary={
                "occupancy": round(archive.occupancy, 4),
                "cells_filled": len(archive.cells),
                "cells_total": archive.total_cells,
                "top": [
                    {
                        "elite_id": r.elite_id,
                        "fitness": r.fitness,
                        "claim": r.candidate.hypothesis.claim,
                        "params": r.candidate.plan.params,
                        "values": r.metrics.values,
                    }
                    for r in elites[:5]
                ],
            },
            writeups=collect_writeups(ws, elites),
            verification=verification_summary,
        )

    cap = metadata.budget.max_usd if metadata.budget.max_usd is not None else "∞"
    body = f"""# Final report — {metadata.project_id}

**Question:** {metadata.question or "_not recorded_"}
**Audience:** {metadata.audience} · **Style:** {metadata.style} · **Domain:** `{config.domain}`
**Spend:** ${spend["usd"]:.4f} of {cap} · **Jobs:** {counts}

> Scope caveat: results below describe only the tasks in domain pack `{config.domain}` as run
> here. They do not license claims about the wider field.

## 1. Narrative

{narrative_text}

## 2. Archive coverage

Occupancy **{len(archive.cells)}/{archive.total_cells}** cells ({archive.occupancy:.1%}).

{_coverage_table(archive)}

## 3. Top elites

{_elite_rows(elites)}

## 4. Verification state

```json
{json.dumps(verification_summary, indent=2)}
```

{"### Recent failures" if failures else ""}
{chr(10).join(f"- `{e['kind']}` {json.dumps(e['payload'])[:160]}" for e in failures[:10])}

## 5. Assumptions carried from Phase 1

{chr(10).join(f"- {a}" for a in metadata.assumptions) or "_none recorded_"}

## 6. Per-experiment writeups

{collect_writeups(ws, elites)}
"""
    ws.write_text(ws.report_path, body)
    return ws.report_path


def _narrative(
    *,
    metadata: Any,
    archive_summary: dict[str, Any],
    writeups: str,
    verification: dict[str, Any],
) -> str:
    try:
        from .agent import context_block, run_skilled

        out = run_skilled(
            "final_report",
            "\n\n".join(
                [
                    "Write the Phase-3 final report narrative.",
                    context_block("audience", metadata.audience),
                    context_block("style", metadata.style),
                    context_block("metadata", json.loads(metadata.model_dump_json())),
                    context_block("archive_summary", archive_summary),
                    context_block("writeups", writeups[:8000]),
                    context_block("verification", verification),
                ]
            ),
            role=(
                "You are the Phase-3 final_report agent for ai_scientist. "
                "Distinguish measured from inferred; report negatives plainly."
            ),
            expect_json=False,
            temperature=0.4,
        )
        return (out.text or "").strip() or f"_narrative empty ({out.model_used})_"
    except Exception as exc:  # noqa: BLE001 - deterministic sections still stand alone
        return f"_narrative unavailable: {type(exc).__name__}: {exc}_"
