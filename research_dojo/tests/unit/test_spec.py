from __future__ import annotations

import os

import pytest
from pydantic import ValidationError

from research_dojo.config.spec import ExperimentSpec, load_spec

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))


def test_load_tom_smoke_spec(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini-test")
    spec = load_spec(os.path.join(REPO_ROOT, "specs", "tom_smoke.yaml"))
    assert spec.experiment_id == "tom_smoke_v1"
    assert spec.model.deployment == "gpt-4o-mini-test"
    assert spec.budget.max_usd == 2.0
    assert spec.verification.judge is not None
    assert spec.verification.judge.version == "2026-08-19"


def test_budget_max_usd_required():
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate({
            "experiment_id": "x",
            "hypothesis": "h",
            "model": {"deployment": "d"},
            "dataset": "data.jsonl",
            "budget": {},  # missing max_usd
        })


def test_judge_version_required_when_judge_configured():
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate({
            "experiment_id": "x",
            "hypothesis": "h",
            "model": {"deployment": "d"},
            "dataset": "data.jsonl",
            "budget": {"max_usd": 1.0},
            "verification": {"judge": {"rubric": "r.md"}},  # missing version
        })


def test_arms_must_be_nonempty():
    with pytest.raises(ValidationError):
        ExperimentSpec.model_validate({
            "experiment_id": "x",
            "hypothesis": "h",
            "model": {"deployment": "d"},
            "dataset": "data.jsonl",
            "arms": [],
            "budget": {"max_usd": 1.0},
        })


def test_spec_hash_stable_across_calls():
    spec = ExperimentSpec.model_validate({
        "experiment_id": "x",
        "hypothesis": "h",
        "model": {"deployment": "d"},
        "dataset": "data.jsonl",
        "budget": {"max_usd": 1.0},
    })
    assert spec.spec_hash() == spec.spec_hash()


def test_env_var_expansion_with_default(monkeypatch, tmp_path):
    monkeypatch.delenv("DOJO_ALERT_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "d1")
    spec_path = tmp_path / "s.yaml"
    spec_path.write_text(
        "experiment_id: x\nhypothesis: h\n"
        "model:\n  deployment: ${AZURE_OPENAI_DEPLOYMENT}\n"
        "dataset: data.jsonl\n"
        "budget:\n  max_usd: 1.0\n"
        "alerts:\n  webhook_url: ${DOJO_ALERT_WEBHOOK_URL:-}\n"
    )
    spec = load_spec(spec_path)
    assert spec.model.deployment == "d1"
    assert spec.alerts.webhook_url == ""
