"""Experiment agent: run one assigned trial end-to-end on `fs`.

This is the DESIGN §6 "experiment agent" — not a free-roaming ReAct loop. The domain pack
owns `run`/`grade`; this agent owns the epistemic hygiene around a trial: validation,
execution, adversarial verification, results writeup, and spend recording.
"""

from __future__ import annotations

import json
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..domain import RunContext, load_domain
from ..fs_layout import Workspace
from ..llm import get_llm
from ..schema import Metrics, Results
from ..skills_loader import SkillRegistry
from .heartbeat import Heartbeat
from .state import StateStore
from .verify import verify_result


class ExperimentAgent:
    """Execute a single queued job as an experiment agent."""

    def __init__(
        self,
        project: str | Path,
        job_id: str,
        *,
        worker_id: str | None = None,
        heartbeat: bool = True,
        store: StateStore | None = None,
    ) -> None:
        self.ws = Workspace(project)
        self.job_id = job_id
        self.worker_id = worker_id
        self.heartbeat_enabled = heartbeat
        self._owns_store = store is None
        self.store = store or StateStore(self.ws.db_path)
        self.config = self.ws.read_config()
        self.job_dir = self.ws.job_dir(job_id)
        (self.job_dir / "logs").mkdir(parents=True, exist_ok=True)
        self.log_path = self.job_dir / "logs" / "trial.log"

    def log(self, message: str) -> None:
        stamp = datetime.now(UTC).isoformat()
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{stamp} {message}\n")

    def run(self) -> int:
        """Returns a process-style exit code (0 ok, 1 failed)."""
        hb = Heartbeat(
            self.store, self.job_id, self.config.ops.heartbeat_interval_s, enabled=self.heartbeat_enabled
        )
        try:
            job = self.store.get_job(self.job_id)
            if job is None:
                raise RuntimeError(f"unknown job {self.job_id}")
            candidate = self.ws.read_candidate(job.candidate_id)
            domain = load_domain(self.config.domain)
            domain.validate_plan(candidate.plan)
            self.ws.write_json(
                self.job_dir / "spec_snapshot.json", json.loads(candidate.model_dump_json())
            )

            with hb:
                hb.beat()
                ctx = RunContext(
                    job_id=self.job_id,
                    seed=candidate.plan.seed,
                    llm=get_llm(),
                    heartbeat=hb.beat,
                    log=self.log,
                    extra={"project": str(self.ws.root), "job_dir": str(self.job_dir)},
                )
                self.log(
                    f"experiment_agent worker={self.worker_id or '-'} "
                    f"running {candidate.plan.plan_id}"
                )
                results = domain.run(candidate.plan, self.job_dir, ctx)
                metrics = domain.grade(candidate.plan, results)

                verification = None
                if self.config.verify.enabled:
                    skills = SkillRegistry().load()
                    verification = verify_result(
                        candidate,
                        metrics,
                        llm=get_llm(),
                        skills=skills,
                        config=self.config.verify,
                    )
                    extra = [f for f in verification.flags if f not in metrics.verification_flags]
                    metrics = metrics.model_copy(
                        update={"verification_flags": metrics.verification_flags + extra}
                    )
                    self.ws.write_json(self.job_dir / "verification.json", verification.to_dict())
                    self.log(
                        f"verification ruling={verification.ruling} flags={verification.flags}"
                    )

                writeup = self._write_up(candidate, metrics)
                self.ws.write_json(
                    self.job_dir / "result.json",
                    {
                        "job_id": self.job_id,
                        "candidate_id": candidate.candidate_id,
                        "results": json.loads(results.model_dump_json()),
                        "metrics": json.loads(metrics.model_dump_json()),
                        "verification": verification.to_dict() if verification else None,
                        "writeup_ref": writeup,
                        "agent": "experiment_agent",
                    },
                )
                self.store.record_spend(
                    self.job_id,
                    float(results.usage.get("usd", 0.0)),
                    float(results.usage.get("tokens", 0.0)),
                )
            self.store.mark_terminal(self.job_id, "done")
            self.store.add_event(
                "job_done", {"job_id": self.job_id, "fitness": metrics.fitness}
            )
            self.log(f"done fitness={metrics.fitness}")
            return 0
        except Exception as exc:  # noqa: BLE001 - a bad trial fails one job, not the fleet
            detail = f"{type(exc).__name__}: {exc}"
            self.log(f"FAILED {detail}\n{traceback.format_exc()}")
            self.ws.write_json(
                self.job_dir / "result.json",
                {
                    "job_id": self.job_id,
                    "error": detail,
                    "results": json.loads(Results(ok=False, error=detail).model_dump_json()),
                    "metrics": None,
                    "agent": "experiment_agent",
                },
            )
            self.store.mark_terminal(self.job_id, "failed", detail)
            self.store.add_event("job_failed", {"job_id": self.job_id, "error": detail})
            return 1
        finally:
            if self._owns_store:
                self.store.close()

    def _write_up(self, candidate: Any, metrics: Metrics) -> str | None:
        try:
            from ..agent import context_block, run_skilled

            out = run_skilled(
                "results_writeup",
                "\n\n".join(
                    [
                        "Write the per-trial lab note.",
                        context_block("job_id", self.job_id),
                        context_block(
                            "hypothesis",
                            {
                                "statement": candidate.hypothesis.statement,
                                "claim": candidate.hypothesis.claim,
                            },
                        ),
                        context_block(
                            "plan",
                            {"params": candidate.plan.params, "seed": candidate.plan.seed},
                        ),
                        context_block(
                            "metrics",
                            {
                                "fitness": metrics.fitness,
                                "values": metrics.values,
                                "flags": metrics.verification_flags,
                            },
                        ),
                        context_block("flags", metrics.verification_flags),
                    ]
                ),
                role=(
                    "You are the results_writeup agent for ai_scientist. "
                    "≤200 words; quote measured numbers only."
                ),
                expect_json=False,
                temperature=0.3,
            )
            text = (out.text or "").strip()
        except Exception as exc:  # noqa: BLE001
            text = f"_writeup unavailable: {type(exc).__name__}: {exc}_"
        header = (
            f"# Results writeup — {self.job_id}\n\n"
            f"**Claim:** {candidate.hypothesis.claim}\n\n"
            f"**Fitness:** {metrics.fitness}\n\n"
        )
        self.ws.write_text(self.job_dir / "results_writeup.md", header + text.strip() + "\n")
        return f"jobs/{self.job_id}/results_writeup.md"
