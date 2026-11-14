# SPDX-License-Identifier: Apache-2.0
"""Inspect entry point: importing this module registers Probo tasks and scorers."""

from probo.scenarios.helpdesk_exfil.leak_checks import (
    note_delivered,
    record_leaked,
    sent_to_watched_address,
)
from probo.scenarios.helpdesk_exfil.scorer import task_completed
from probo.scenarios.helpdesk_exfil.task import helpdesk_exfil

__all__ = [
    "helpdesk_exfil",
    "note_delivered",
    "record_leaked",
    "sent_to_watched_address",
    "task_completed",
]
