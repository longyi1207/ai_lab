"""`oversight_debate` pack: task generation, protocols, and paired-control grading.

The model is simulated by `ScriptedJudgeLLM`, whose judge competence is a knob. That lets the
tests assert the *measurement* is sound — a helpful protocol shows a positive `delta_vs_solo`,
a useless one does not — without spending money or pretending a toy result is science.
"""

from __future__ import annotations

import json

import pytest

from ai_scientist.domain import PlanInvalid, load_domain
from ai_scientist.domain.base import RunContext, validate_metrics
from ai_scientist.domain.oversight_debate import build_suite, run_task
from ai_scientist.domain.oversight_debate.protocols import _parse_judge
from ai_scientist.llm import LLMResponse


class ScriptedJudgeLLM:
    """Simulated seats: advocates restate their assigned option; the judge follows a rule.

    The judge is deliberately given **no oracle**. It can only do what a real evidence-poor
    judge can do: read the transcript, or guess when there is none.

    - `follow` = `"honest"` → takes the option the `affirm` (truth-notes) advocate defended
    - `follow` = `"dishonest"` → takes the `deny` (lie-notes) advocate's option
    - with no transcript it always answers `solo_pick` (a fixed guess), so unaided accuracy is
      roughly the base rate of gold landing in that position
    """

    name = "scripted"

    def __init__(self, *, follow: str = "honest", solo_pick: str = "A") -> None:
        self.follow = follow
        self.solo_pick = solo_pick
        self.calls: list[str] = []
        self.judge_prompts: list[str] = []

    def complete(self, system, user, *, temperature=0.7, json_mode=False) -> LLMResponse:
        self.calls.append(system)
        usage = {"tokens": 40.0}
        # Advocate seats (legacy prose or Agent+skill XML).
        if "Defend option " in user or "Active skill hint: oversight_advocate" in system:
            defend = _xml_or_defend_letter(user)
            side = _xml_tag(user, "side") or (
                "affirm" if "as the affirm advocate" in user else "deny"
            )
            return LLMResponse(
                text=f"My notes support {defend}. Option {defend} is correct. ({side})",
                usage=usage,
            )
        self.judge_prompts.append(user)
        pick = self.solo_pick
        claims = _claims_by_role(user)
        if claims:
            preferred = claims.get(self.follow_role())
            pick = preferred or next(iter(claims.values()), self.solo_pick)
        return LLMResponse(
            text=json.dumps({"answer": pick, "winner": "affirm", "confidence": 0.5}), usage=usage
        )

    def follow_role(self) -> str:
        return "affirm" if self.follow == "honest" else "deny"


def _xml_tag(blob: str, tag: str) -> str | None:
    import re

    match = re.search(rf"<{tag}>\s*(.*?)\s*</{tag}>", blob, flags=re.S)
    return match.group(1).strip() if match else None


def _xml_or_defend_letter(user: str) -> str:
    letter = _xml_tag(user, "defend_letter")
    if letter:
        return letter.strip().upper()[:1]
    return user.split("Defend option ")[1][0]


def _claims_by_role(user: str) -> dict[str, str]:
    """Map transcript role → the option letter that role defended."""
    import re

    transcript = _xml_tag(user, "transcript")
    if transcript is None:
        if "Transcript:\n" not in user:
            return {}
        transcript = user.split("Transcript:\n", 1)[1]
    if not transcript.strip():
        return {}
    out: dict[str, str] = {}
    for role, letter in re.findall(
        r"\[(affirm|deny)\] .*?Option ([ABCD]) is correct", transcript, flags=re.S
    ):
        out.setdefault(role, letter)
    return out


# --------------------------------------------------------------------- tasks
def test_suite_is_deterministic_and_split():
    a, b = build_suite(7), build_suite(7)
    assert [t.task_id for t in a.get("train")] == [t.task_id for t in b.get("train")]
    assert a.get("train")[0].question == b.get("train")[0].question
    assert set(a.splits) == {"train", "heldout", "probe"}
    assert len(a.get("train")) == 12 and len(a.get("probe")) == 8
    # a different suite seed gives different worlds
    assert [t.gold for t in build_suite(8).get("train")] != [t.gold for t in a.get("train")]


def test_tasks_carry_asymmetric_notes_and_consistent_options():
    for task in build_suite(3).get("train"):
        assert task.gold in task.options and task.lie_answer in task.options
        assert task.gold != task.lie_answer
        assert len(set(task.options)) == 4
        # truth notes entail the gold answer; lie notes assert the wrong one
        assert task.gold in task.truth_notes
        assert task.lie_answer in task.lie_notes
        assert task.gold not in task.lie_notes
        assert task.gold_letter != task.lie_letter


def test_gold_letter_is_not_always_position_a():
    letters = {t.gold_letter for t in build_suite(11).get("train")}
    assert len(letters) > 1, "gold option position must vary or the judge can cheat on position"


def test_judge_parser_handles_json_prose_and_garbage():
    assert _parse_judge('{"answer": "C", "winner": "deny"}') == ("C", "deny", True)
    assert _parse_judge("I think the answer is B.")[0] == "B"
    assert _parse_judge("no letters here") == (None, None, False)


def test_judge_parser_does_not_accept_an_empty_answer():
    """A reply with no answer is a parse failure; counting it as parsed inflates parse_rate."""
    assert _parse_judge('{"answer": "", "winner": "affirm"}') == (None, None, False)
    assert _parse_judge('{"fake": true, "digest": "aa670d84"}') == (None, None, False)
    assert _parse_judge('{"answer": "Z"}') == (None, None, False)


# --------------------------------------------------------------------- protocols
def test_solo_protocol_asks_the_judge_without_advocates():
    task = build_suite(5).get("train")[0]
    llm = ScriptedJudgeLLM()
    outcome = run_task(task, llm, {"protocol": "solo"})
    assert outcome.transcript == []
    assert outcome.parse_ok
    assert len(llm.judge_prompts) == 1
    assert "No advocates spoke" in llm.judge_prompts[0]
    assert all("Defend option" not in call for call in llm.calls)


def test_debate_runs_both_sides_each_round_with_assigned_options():
    task = build_suite(5).get("train")[0]
    llm = ScriptedJudgeLLM()
    outcome = run_task(task, llm, {"protocol": "debate", "rounds": 2})
    roles = [turn.role for turn in outcome.transcript]
    assert roles == ["affirm", "deny", "affirm", "deny"]
    assert f"Option {task.gold_letter} is correct" in outcome.transcript[0].content
    assert f"Option {task.lie_letter} is correct" in outcome.transcript[1].content
    assert outcome.truth_side_won is not None


def test_deny_speaks_first_flips_order():
    task = build_suite(5).get("train")[0]
    outcome = run_task(
        task, ScriptedJudgeLLM(), {"protocol": "debate", "rounds": 1, "deny_speaks_first": True}
    )
    assert [t.role for t in outcome.transcript] == ["deny", "affirm"]


def test_consultancy_can_be_honest_or_dishonest():
    task = build_suite(5).get("train")[0]
    honest = run_task(
        task, ScriptedJudgeLLM(), {"protocol": "consultancy", "consultancy_honest": True}
    )
    liar = run_task(
        task, ScriptedJudgeLLM(), {"protocol": "consultancy", "consultancy_honest": False}
    )
    assert len(honest.transcript) == 1 and honest.transcript[0].role == "affirm"
    assert liar.transcript[0].role == "deny"


def test_judge_never_sees_notes_unless_asymmetry_disabled():
    task = build_suite(5).get("train")[0]

    asymmetric = ScriptedJudgeLLM()
    run_task(task, asymmetric, {"protocol": "debate", "rounds": 1})
    assert asymmetric.judge_prompts, "judge must be called"
    assert task.truth_notes not in asymmetric.judge_prompts[0]
    assert task.lie_notes not in asymmetric.judge_prompts[0]

    disabled = ScriptedJudgeLLM()
    run_task(task, disabled, {"protocol": "debate", "rounds": 1, "judge_sees_notes": True})
    assert task.truth_notes in disabled.judge_prompts[0]


def test_unknown_protocol_is_rejected():
    task = build_suite(5).get("train")[0]
    with pytest.raises(ValueError, match="unknown protocol"):
        run_task(task, ScriptedJudgeLLM(), {"protocol": "telepathy"})


# --------------------------------------------------------------------- pack
@pytest.fixture
def pack():
    return load_domain("oversight_debate")


def _run_and_grade(pack, tmp_path, llm, params, seed=7):
    candidate = pack.seed_candidates()[0]
    plan = candidate.plan.model_copy(
        update={"params": {**candidate.plan.params, **params}, "seed": seed}
    )
    pack.validate_plan(plan)
    ctx = RunContext(job_id="job_t", seed=seed, llm=llm)
    results = pack.run(plan, tmp_path, ctx)
    metrics = pack.grade(plan, results)
    validate_metrics(pack, metrics)
    return results, metrics


def test_pack_validates_plans(pack):
    candidate = pack.seed_candidates()[2]
    pack.validate_plan(candidate.plan)
    for bad in ({"protocol": "seance"}, {"rounds": 9}, {"n_tasks": 99}, {"debater_style": "snark"}):
        plan = candidate.plan.model_copy(update={"params": {**candidate.plan.params, **bad}})
        with pytest.raises(PlanInvalid):
            pack.validate_plan(plan)


def test_pack_seeds_cover_control_and_treatments(pack):
    protocols = {c.plan.params["protocol"] for c in pack.seed_candidates()}
    assert protocols == {"solo", "consultancy", "debate"}
    for candidate in pack.seed_candidates():
        pack.validate_plan(candidate.plan)
        assert candidate.plan.baselines, "every seed must name its comparison"
        assert candidate.plan.notes, "every seed must state what would falsify it"


def test_helpful_protocol_scores_positive_delta(pack, tmp_path):
    """Judge can follow the honest advocate; alone it only guesses → debate must show a gain."""
    llm = ScriptedJudgeLLM(follow="honest")
    _, metrics = _run_and_grade(
        pack, tmp_path, llm, {"protocol": "debate", "rounds": 1, "n_tasks": 6}
    )

    assert metrics.values["judge_accuracy"] == 1.0  # the honest side always defends gold
    assert metrics.values["solo_accuracy"] < 1.0  # a fixed guess cannot track gold position
    assert metrics.values["delta_vs_solo"] > 0
    assert metrics.fitness > 0
    assert metrics.values["parse_rate"] == 1.0
    assert metrics.values["truth_win_rate"] == 1.0
    assert len(metrics.behavior) >= 4


def test_protocol_that_misleads_the_judge_is_penalized(pack, tmp_path):
    """Judge follows the dishonest advocate: the same machinery must report a loss, not a win."""
    llm = ScriptedJudgeLLM(follow="dishonest")
    _, metrics = _run_and_grade(
        pack, tmp_path, llm, {"protocol": "debate", "rounds": 1, "n_tasks": 6}
    )

    assert metrics.values["judge_accuracy"] == 0.0  # the lie side never defends gold
    assert metrics.values["delta_vs_solo"] < 0
    assert metrics.values["truth_win_rate"] == 0.0
    assert metrics.fitness < 0


def test_solo_arm_is_flagged_as_control_only(pack, tmp_path):
    llm = ScriptedJudgeLLM()
    _, metrics = _run_and_grade(pack, tmp_path, llm, {"protocol": "solo", "n_tasks": 4})
    assert "control_arm_only" in metrics.verification_flags
    # treatment and control are the same protocol here, so the delta must be exactly zero
    assert metrics.values["delta_vs_solo"] == pytest.approx(0.0)


def test_truth_win_rate_is_absent_when_not_applicable(pack, tmp_path):
    """Reporting 0.0 for a one-sided protocol would read as 'the honest side never won'."""
    llm = ScriptedJudgeLLM()
    _, solo = _run_and_grade(pack, tmp_path, llm, {"protocol": "solo", "n_tasks": 4})
    assert "truth_win_rate" not in solo.values

    _, consultancy = _run_and_grade(
        pack, tmp_path, llm, {"protocol": "consultancy", "n_tasks": 4}
    )
    assert "truth_win_rate" not in consultancy.values

    _, debate = _run_and_grade(
        pack, tmp_path, llm, {"protocol": "debate", "rounds": 1, "n_tasks": 4}
    )
    assert debate.values["truth_win_rate"] == 1.0


def test_disabling_asymmetry_is_flagged(pack, tmp_path):
    llm = ScriptedJudgeLLM()
    _, metrics = _run_and_grade(
        pack,
        tmp_path,
        llm,
        {"protocol": "debate", "rounds": 1, "n_tasks": 4, "judge_sees_notes": True},
    )
    assert "asymmetry_disabled" in metrics.verification_flags


def test_unparseable_judge_lowers_parse_rate_and_flags(pack, tmp_path):
    from ai_scientist.llm import FakeLLM

    _, metrics = _run_and_grade(
        pack, tmp_path, FakeLLM(), {"protocol": "debate", "rounds": 1, "n_tasks": 4}
    )
    assert metrics.values["parse_rate"] < 0.8
    assert "low_parse_rate" in metrics.verification_flags


def test_pack_writes_transcripts_and_accounts_cost(pack, tmp_path):
    llm = ScriptedJudgeLLM()
    results, metrics = _run_and_grade(
        pack, tmp_path, llm, {"protocol": "debate", "rounds": 2, "n_tasks": 4}
    )
    transcripts = json.loads((tmp_path / "artifacts" / "transcripts.json").read_text())
    assert set(transcripts) == {
        "train_treatment",
        "train_control",
        "probe_treatment",
        "probe_control",
    }
    assert transcripts["train_treatment"][0]["transcript"]
    assert transcripts["train_control"][0]["transcript"] == []  # control is unaided
    assert results.usage["tokens"] > 0 and metrics.descriptor["cost"] > 0


def test_pack_requires_an_llm(pack, tmp_path):
    candidate = pack.seed_candidates()[0]
    with pytest.raises(RuntimeError, match="needs an LLM"):
        pack.run(candidate.plan, tmp_path, RunContext(job_id="j", seed=1, llm=None))


def test_pack_runs_through_the_harness_end_to_end(tmp_path, monkeypatch):
    """Same daemon loop as fake_toy, but on the real pack with a scripted model."""
    from ai_scientist.daemon import Daemon
    from ai_scientist.fs_layout import Workspace
    from ai_scientist.ops import run_job
    from ai_scientist.schema import Budget, EngineConfig, Metadata

    monkeypatch.setattr("ai_scientist.ops.experiment_agent.get_llm", lambda: ScriptedJudgeLLM())
    ws = Workspace(tmp_path / "od")
    config = EngineConfig(domain="oversight_debate")
    config.ops.concurrency = 1
    config.search.target_inflight = 2
    config.search.offspring_per_tick = 1
    config.verify.enabled = False  # verification model is out of scope for this test
    ws.init(
        metadata=Metadata(
            project_id="od", question="does debate help a weak judge?", budget=Budget(max_usd=5.0)
        ),
        config=config,
    )

    daemon = Daemon.__new__(Daemon)

    def spawn(job, worker_id):
        run_job(ws.root, job.job_id, worker_id=worker_id, store=daemon.store)
        return None

    Daemon.__init__(daemon, ws.root, spawn=spawn, seed=1)
    try:
        daemon.store.set_runtime("job_budget", 4)
        outcome = daemon.run_until_idle(timeout_s=120)
        status = daemon.c_status()
    finally:
        daemon.stop()

    assert not outcome["timed_out"]
    assert status["jobs"].get("done", 0) >= 3
    assert status["search"]["cells_filled"] >= 1
    best = status["search"]["best"]
    assert best is not None and "protocol" in best["params"]
