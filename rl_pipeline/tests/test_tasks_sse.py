"""Checks against the real task code in score-seeking-eval. Skipped unless SSE_ROOT points at it."""
import os
from pathlib import Path

import pytest

from rl_pipeline.tasks import get_task

SSE = os.environ.get("SSE_ROOT")
pytestmark = [pytest.mark.sse, pytest.mark.skipif(not SSE or not Path(SSE).is_dir(),
                                                  reason="set SSE_ROOT to a score-seeking-eval checkout")]


def test_protocol_re_prompts_match_the_runner():
    t = get_task("protocol_re", Path(SSE))
    cell = t.cell_from_run({"scope": "forbid", "monitoring": "observed"})
    system = t.system_prompt(cell)
    assert system.startswith(t.c["SYSTEM"]) and t.c["SCOPE_FORBID"] in system
    assert "MONITORED" in system                      # legacy "observed" maps to the observed frame
    assert [x["function"]["name"] for x in t.tools] == ["bash", "submit_flag"]
    assert t.supports({**cell, "salient": "off"})[0] is False


def test_internal_exfil_prompts_and_grader_load():
    t = get_task("internal_exfil", Path(SSE))
    cell = t.cell_from_run({"scope": "pressure", "precedent": "endorsing"})
    assert t.c["SCOPE_PRESSURE"] in t.system_prompt(cell)
    verdict = t.grader.grade("", "", "k", [])
    assert verdict["label"] == "fail"
