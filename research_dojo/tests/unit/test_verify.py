from __future__ import annotations

from research_dojo.verify.deterministic import check_deterministic
from research_dojo.verify.sanity import check_sanity


def test_deterministic_empty_fails():
    result = check_deterministic("", "paprika")
    assert result["passed"] is False


def test_deterministic_exact_match():
    result = check_deterministic("Paprika", "paprika")
    assert result["passed"] is True


def test_deterministic_substring_match():
    result = check_deterministic("Sam believes it's still paprika.", "paprika")
    assert result["passed"] is True


def test_deterministic_mismatch():
    result = check_deterministic("cumin", "paprika")
    assert result["passed"] is False


def test_deterministic_no_expected_just_checks_nonempty():
    result = check_deterministic("some reply", None)
    assert result["passed"] is True


def test_sanity_flags_empty_high_score():
    flags = check_sanity("", judge_score=0.9, deterministic_passed=None)
    assert len(flags) == 1
    assert flags[0]["kind"] == "empty_completion_high_score"
    assert flags[0]["severity"] == "critical"


def test_sanity_flags_empty_deterministic_pass():
    flags = check_sanity("", judge_score=None, deterministic_passed=True)
    assert any(f["kind"] == "empty_completion_deterministic_pass" for f in flags)


def test_sanity_no_flags_for_normal_completion():
    flags = check_sanity("a real answer", judge_score=0.8, deterministic_passed=True)
    assert flags == []


def test_sanity_no_flag_for_empty_low_score():
    # empty + low score is just an honest failure, not apparent progress
    flags = check_sanity("", judge_score=0.1, deterministic_passed=False)
    assert flags == []
