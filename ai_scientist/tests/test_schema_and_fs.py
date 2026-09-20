from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_scientist.domain import PlanInvalid, load_domain
from ai_scientist.fs_layout import Workspace
from ai_scientist.schema import Axis, Candidate, ExperimentPlan, Hypothesis, Metadata


def _candidate(**params) -> Candidate:
    hyp = Hypothesis(statement="s", claim="c")
    plan = ExperimentPlan(
        hypothesis_id=hyp.hypothesis_id,
        domain="fake_toy",
        params={"alpha": 0.5, "rounds": 2, "mode": "debate", **params},
    )
    return Candidate(hypothesis=hyp, plan=plan)


def test_candidate_requires_matching_hypothesis_id():
    hyp = Hypothesis(statement="s", claim="c")
    plan = ExperimentPlan(hypothesis_id="hyp_other", domain="fake_toy", params={})
    with pytest.raises(ValidationError):
        Candidate(hypothesis=hyp, plan=plan)


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        Hypothesis(statement="s", claim="c", not_a_field=1)


def test_domain_rejects_invalid_plans(domain):
    domain.validate_plan(_candidate().plan)
    with pytest.raises(PlanInvalid):
        domain.validate_plan(_candidate(alpha=3.0).plan)
    with pytest.raises(PlanInvalid):
        domain.validate_plan(_candidate(rounds=99).plan)
    with pytest.raises(PlanInvalid):
        domain.validate_plan(_candidate(mode="telepathy").plan)


def test_plan_with_gpu_request_rejected_by_toy_domain(domain):
    candidate = _candidate()
    candidate.plan.resources.gpu = 1
    with pytest.raises(PlanInvalid):
        domain.validate_plan(candidate.plan)


def test_axis_edges_must_increase():
    with pytest.raises(ValidationError):
        Axis(name="bad", edges=[0.0, 0.0, 1.0])


def test_axis_binning_is_clamped():
    axis = Axis(name="q", edges=[0.0, 0.5, 1.0])
    assert axis.bin_for(-5.0) == 0
    assert axis.bin_for(0.25) == 0
    assert axis.bin_for(0.5) == 1
    assert axis.bin_for(99.0) == 1


def test_fingerprint_ignores_ids_but_tracks_params():
    a, b = _candidate(), _candidate()
    assert a.candidate_id != b.candidate_id
    assert a.fingerprint() == b.fingerprint()
    assert a.fingerprint() != _candidate(alpha=0.9).fingerprint()


def test_workspace_roundtrip_and_atomic_writes(project: Workspace):
    assert project.initialized
    metadata = project.read_metadata()
    assert metadata.project_id == "study"
    assert project.read_config().domain == "fake_toy"

    candidate = load_domain("fake_toy").seed_candidates()[0]
    project.write_candidate(candidate)
    loaded = project.read_candidate(candidate.candidate_id)
    assert loaded.plan.params == candidate.plan.params

    # no stray temp files left behind by the atomic write path
    assert not list(project.candidates_dir.glob(".*tmp"))


def test_metadata_never_stores_secret_values(project: Workspace):
    metadata = project.read_metadata()
    assert metadata.credentials_refs
    raw = project.metadata_path.read_text()
    for ref in metadata.credentials_refs:
        assert ref in raw
    assert "sk-" not in raw


def test_metadata_rejects_unknown_style():
    with pytest.raises(ValidationError):
        Metadata(project_id="p", style="poetic")
