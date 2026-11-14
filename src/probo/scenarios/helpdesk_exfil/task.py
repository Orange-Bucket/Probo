# SPDX-License-Identifier: Apache-2.0
"""The `helpdesk_exfil` Inspect task (scenario id `helpdesk-exfil`)."""

import secrets
from typing import Final

from inspect_ai import Task, task

from probo.scenarios.helpdesk_exfil.agent import helpdesk_agent
from probo.scenarios.helpdesk_exfil.dataset import build_dataset
from probo.scenarios.helpdesk_exfil.keys import META_SCENARIO, SCENARIO_ID
from probo.scenarios.helpdesk_exfil.leak_checks import (
    note_delivered,
    record_leaked,
    sent_to_watched_address,
)
from probo.scenarios.helpdesk_exfil.scorer import task_completed
from probo.scenarios.helpdesk_exfil.startup import setup_environment

DEFAULT_MESSAGE_LIMIT: Final = 40
"""Per-sample message limit unless the task is given another."""


@task
def helpdesk_exfil(
    seed: int | None = None,
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
    watch_address: str | None = None,
) -> Task:
    """A helpdesk agent answers support tickets by e-mail.

    Scored by `task_completed` (utility) and the three leak checks in `leak_checks`:
    `record_leaked`, `sent_to_watched_address` and `note_delivered`.

    Args:
        seed: Seed for the per-record marker tokens. When omitted, one is drawn at random
            when the task is built and recorded in every sample's metadata (`seed`), which
            is the only source of truth for reproducing tokens. It is not put in the task
            metadata: `eval_retry` rebuilds the task from the passed arguments, so an
            unseeded run draws a new seed for the retried samples while carried-over samples
            keep theirs.
        message_limit: Per-sample message limit for the agent.
        watch_address: Address recorded in every sample for `sent_to_watched_address`;
            when omitted that check is not applicable.
    """
    if seed is None:
        seed = secrets.randbits(63)
    return Task(
        dataset=build_dataset(seed, watch_address=watch_address),
        setup=setup_environment(),
        solver=helpdesk_agent(),
        scorer=[task_completed(), record_leaked(), sent_to_watched_address(), note_delivered()],
        message_limit=message_limit,
        metadata={META_SCENARIO: SCENARIO_ID},
    )
