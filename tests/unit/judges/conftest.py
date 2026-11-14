# SPDX-License-Identifier: Apache-2.0
"""Logs shared by the grader tests, each built once by running the helpdesk task."""

import pytest
from inspect_ai.log import EvalLog

from ..scenarios.helpdesk_support import run
from .cases import (
    MIX,
    PROBE,
    PROBE_GRADER_CALLS,
    PROBE_GRADER_CONFIG,
    PROBE_GRADES,
    mix_grader_rule,
    mix_turn_text,
)
from .judge_support import case_agent, case_task, grader


@pytest.fixture(scope="session")
def mix_log(tmp_path_factory: pytest.TempPathFactory) -> EvalLog:
    """The calibration log: one sample per `MIX` case, graded by `mix_grader_rule`; the agent
    writes `mix_turn_text` on every turn."""
    tmp_path = tmp_path_factory.mktemp("mix")
    return run(
        tmp_path,
        model=case_agent(MIX, turn_text=mix_turn_text),
        task=case_task(MIX, tmp_path / "empty-corpus"),
        model_roles={"judge": grader(mix_grader_rule)},
    )


@pytest.fixture(scope="session")
def probe_log(tmp_path_factory: pytest.TempPathFactory) -> EvalLog:
    """One sample per `PROBE` case, graded by `PROBE_GRADES` with `PROBE_GRADER_CONFIG`."""
    tmp_path = tmp_path_factory.mktemp("probe")
    return run(
        tmp_path,
        model=case_agent(PROBE),
        task=case_task(PROBE, tmp_path / "empty-corpus"),
        model_roles={"judge": grader(PROBE_GRADES, PROBE_GRADER_CALLS, PROBE_GRADER_CONFIG)},
    )
