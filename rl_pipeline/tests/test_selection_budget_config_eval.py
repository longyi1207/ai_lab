import json

import pytest
from conftest import entries_for

from rl_pipeline.budget import Budget, BudgetExceeded, Usage
from rl_pipeline.config import load_config
from rl_pipeline.decision_points import locate_onset, select_branch_points, split_of
from rl_pipeline.evaluate import paired_delta, wilson


def episode(eid, quote_step, status="planned", reward=0, reason="action_cheat"):
    turns = [(s, f"step {s} text" + (" I could just use the maintenance key to unlock it" if s == quote_step else ""),
              [], []) for s in range(1, 8)]
    return {"episode_id": eid, "task": "fake", "cell": {}, "model": "m", "transcript": entries_for(*turns),
            "reward": {"reward": reward, "reason": reason},
            "intent_judge": {"intent_status": status, "evidence_quotes": ["I could just use the maintenance key to unlock it"]}}


def test_locate_onset_finds_first_quoted_step():
    assert locate_onset(episode("e", 4))[0] == 4


def test_branch_is_margin_steps_before_onset_and_skips_early_onsets():
    bps, skipped = select_branch_points([episode("a", 5), episode("b", 2)], margin=1, max_per_task=10,
                                        include_temptation=True, test_fraction=0.0, seed=0)
    assert [(b["episode_id"], b["branch_step"]) for b in bps] == [("a", 4)]
    assert skipped["onset_too_early"] == 1


def test_temptation_points_are_optional():
    tempted = episode("t", 5, status="noticed", reward=1, reason="clean_completion")
    assert select_branch_points([tempted], margin=1, max_per_task=10, include_temptation=False,
                                test_fraction=0.0, seed=0)[0] == []
    assert len(select_branch_points([tempted], margin=1, max_per_task=10, include_temptation=True,
                                    test_fraction=0.0, seed=0)[0]) == 1


def test_split_is_stable():
    assert split_of("ep_123", 0.25) == split_of("ep_123", 0.25)
    assert split_of("ep_123", 0.0) == "train" and split_of("ep_123", 1.0) == "test"


def test_budget_costs_caps_and_persists(tmp_path):
    prices = {"cheap": {"input": 1.0, "output": 2.0}, "pricey": {"input": 10.0, "output": 20.0}}
    b = Budget(0.003, prices, tmp_path / "spend.jsonl")
    assert b.record("cheap", Usage(1000, 500), purpose="t") == pytest.approx(0.002)
    assert b.cost("unknown-model", Usage(1000, 0)) == pytest.approx(0.01)   # charged at the max rate
    b.record("cheap", Usage(1000, 0), purpose="t")
    with pytest.raises(BudgetExceeded):
        b.check()
    assert Budget(1.0, prices, tmp_path / "spend.jsonl").spent == pytest.approx(0.003)


def test_config_expands_env_and_rejects_unknown_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("MY_SSE", "/somewhere/sse")
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("run_name: t\npaths:\n  score_seeking_eval: ${MY_SSE}\n  output_dir: out\n"
                        "azure:\n  env_file: null\n")
    cfg = load_config(cfg_file)
    assert str(cfg.paths.score_seeking_eval) == "/somewhere/sse"
    assert cfg.paths.output_dir == tmp_path / "out"
    assert cfg.runs_dir == cfg.paths.score_seeking_eval / "runs"
    cfg_file.write_text("run_name: t\nsample:\n  kk: 3\nazure:\n  env_file: null\n")
    with pytest.raises(ValueError, match="unknown config key"):
        load_config(cfg_file)


def test_set_overrides_are_typed(tmp_path):
    from rl_pipeline.cli import apply_overrides
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text("run_name: t\nazure:\n  env_file: null\n")
    cfg = load_config(cfg_file)
    apply_overrides(cfg, ["sample.k=8", "local.grpo_lr=3e-5", "pairs.include_recorded=true", "local.model=foo/bar"])
    assert cfg.sample.k == 8 and cfg.local.grpo_lr == pytest.approx(3e-5)
    assert cfg.pairs.include_recorded is True and cfg.local.model == "foo/bar"
    with pytest.raises(SystemExit):
        apply_overrides(cfg, ["sample.nope=1"])


def test_wilson_and_paired_delta():
    assert wilson(0, 0) == (0.0, 0.0)
    lo, hi = wilson(5, 10)
    assert lo < 0.5 < hi
    recs = [{"status": "ok", "branch_id": b, "policy": p, "reward": {"reward": r}}
            for b, p, r in (("x", "base", 0), ("x", "tuned", 1), ("y", "base", 1), ("y", "tuned", 1))]
    d = paired_delta(recs, "base", "tuned")
    assert d["branch_points"] == 2 and d["mean_delta_reward"] == 0.5 and d["improved"] == 1
