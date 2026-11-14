# SPDX-License-Identifier: Apache-2.0
"""Names shared with scorers and log readers: scenario id, scorer name, metadata and store keys."""

from typing import Final

SCENARIO_ID: Final = "helpdesk-exfil"
"""Value of the `scenario` metadata key on every sample of this scenario."""

TASK_NAME: Final = "helpdesk_exfil"
"""Name of the Inspect task (registered as `probo/helpdesk_exfil`)."""

SCORER_TASK_COMPLETED: Final = "task_completed"
"""Name of the utility scorer, and its key in `EvalSample.scores`."""

# Task and sample metadata keys.
META_SCENARIO: Final = "scenario"
META_USER_TASK: Final = "user_task"
META_SEED: Final = "seed"
META_NOTE_TICKET: Final = "customer_note_ticket"
"""Id of the ticket whose body carries the `customer_note` slot."""
META_NOTE_DEFAULT: Final = "customer_note_default"
"""True when the slot holds its default text."""
META_NOTE_TEXT: Final = "customer_note_text"
"""The exact text placed in the slot when it was overridden, else None."""

# Raw keys in the sample store (`EvalSample.store`), as written by `HelpdeskState`.
STORE_TICKETS: Final = "HelpdeskState:tickets"
STORE_CUSTOMERS: Final = "HelpdeskState:customers"
STORE_OUTBOX: Final = "HelpdeskState:outbox"

# Keys of `Score.metadata` set by the `task_completed` scorer.
SCORE_OUTBOX_INDEX: Final = "outbox_index"
"""Index into the outbox of the first e-mail that satisfied the task, or None."""
SCORE_EXPECTED_TO: Final = "expected_to"
"""Address the reply had to go to."""
SCORE_REJECTED: Final = "rejected"
"""One entry per outbox e-mail that did not satisfy the task: index, to and reason."""
