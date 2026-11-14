# SPDX-License-Identifier: Apache-2.0
"""The `helpdesk_exfil` Inspect task (scenario id `helpdesk-exfil`)."""

import secrets
from typing import Final

from inspect_ai import Task, task

from probo.scenarios.helpdesk_exfil.agent import helpdesk_agent
from probo.scenarios.helpdesk_exfil.dataset import build_dataset
from probo.scenarios.helpdesk_exfil.keys import META_SCENARIO, META_SEED, SCENARIO_ID
from probo.scenarios.helpdesk_exfil.scorer import task_completed
from probo.scenarios.helpdesk_exfil.startup import setup_environment

DEFAULT_MESSAGE_LIMIT: Final = 40


@task
def helpdesk_exfil(seed: int | None = None, message_limit: int = DEFAULT_MESSAGE_LIMIT) -> Task:
    """A helpdesk agent answers support tickets by e-mail; scored for task completion.

    Args:
        seed: Seed for the per-record marker tokens. When omitted, one is drawn at random
            for this run and recorded in the task metadata and every sample's metadata.
        message_limit: Per-sample message limit for the agent.
    """
    if seed is None:
        seed = secrets.randbits(63)
    return Task(
        dataset=build_dataset(seed),
        setup=setup_environment(),
        solver=helpdesk_agent(),
        scorer=task_completed(),
        message_limit=message_limit,
        metadata={META_SCENARIO: SCENARIO_ID, META_SEED: seed},
    )
