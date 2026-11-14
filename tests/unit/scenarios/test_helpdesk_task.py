# SPDX-License-Identifier: Apache-2.0
"""Task configuration: the message limit stops a runaway agent and the sample is still scored."""

from pathlib import Path

from probo.scenarios.helpdesk_exfil.keys import SCORE_EMAILS
from probo.scenarios.helpdesk_exfil.task import DEFAULT_MESSAGE_LIMIT

from .helpdesk_support import Call, completed, run, samples_by_id, scripted_agent

# Longer than the limit but finite: without the task's limit the script would end on its
# own, and the test would fail on the missing limit instead of hanging.
RUNAWAY: list[Call] = [("list_tickets", {})] * (3 * DEFAULT_MESSAGE_LIMIT)


def test_message_limit_ends_sample_and_it_is_scored(tmp_path: Path) -> None:
    """A sample that keeps calling tools stops at the task's message_limit and is scored."""
    log = run(tmp_path, scripted_agent(lambda prompt: RUNAWAY), task_args={"seed": 1})
    for sample in samples_by_id(log).values():
        assert sample.limit is not None
        assert sample.limit.type == "message"
        assert sample.limit.limit == DEFAULT_MESSAGE_LIMIT
        assert len(sample.messages) == DEFAULT_MESSAGE_LIMIT
        score = completed(sample)
        assert score.value is False
        assert score.metadata is not None
        assert score.metadata[SCORE_EMAILS] == []
