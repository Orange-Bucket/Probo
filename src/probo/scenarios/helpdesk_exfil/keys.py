# SPDX-License-Identifier: Apache-2.0
"""Names shared with scorers and log readers: scenario id, scorer name, metadata and store keys."""

from typing import Final

SCENARIO_ID: Final = "helpdesk-exfil"
"""Value of the `scenario` metadata key, and a part of every marker token's derivation."""

TASK_NAME: Final = "helpdesk_exfil"
"""Name of the Inspect task (registered as `probo/helpdesk_exfil`)."""

SCORER_TASK_COMPLETED: Final = "task_completed"
"""Name of the utility scorer, and its key in `EvalSample.scores`."""

# Sample metadata keys (`META_SCENARIO` is also a task metadata key).
META_SCENARIO: Final = "scenario"
"""The scenario id, `SCENARIO_ID`."""
META_USER_TASK: Final = "user_task"
"""Id of the sample's user task."""
META_SEED: Final = "seed"
"""The seed the sample's marker tokens are derived from.

This per-sample value is the only source of truth for deriving or reproducing tokens. It is
deliberately not in the task metadata: `eval_retry` rebuilds the task from the arguments
originally passed, so an unseeded run draws a new seed on retry, and samples carried over
from the first attempt keep the seed they ran with.
"""
META_NOTE_TICKET: Final = "customer_note_ticket"
"""Id of the ticket whose body carries the `customer_note` slot."""
META_NOTE_DEFAULT: Final = "customer_note_default"
"""True when the slot holds its default text."""
META_NOTE_TEXT: Final = "customer_note_text"
"""The exact text placed in the slot, default or not."""

# Raw keys in the sample store (`EvalSample.store`), as written by `HelpdeskState`.
STORE_TICKETS: Final = "HelpdeskState:tickets"
"""List of `Ticket` records."""
STORE_CUSTOMERS: Final = "HelpdeskState:customers"
"""List of `Customer` records, recovery codes included."""
STORE_OUTBOX: Final = "HelpdeskState:outbox"
"""List of `Email` records, in the order the agent sent them."""

# Keys of `Score.metadata` set by the `task_completed` scorer.
SCORE_OUTBOX_INDEX: Final = "outbox_index"
"""Index into the outbox of the first e-mail that satisfied the task, or None."""
SCORE_EXPECTED_TO: Final = "expected_to"
"""Address the reply had to go to."""
SCORE_EMAILS: Final = "emails"
"""One entry per outbox e-mail, in outbox order, with the `EMAIL_*` keys below."""

# Keys of each `SCORE_EMAILS` entry.
EMAIL_INDEX: Final = "index"
"""Index of the e-mail in the outbox."""
EMAIL_TO: Final = "to"
"""The e-mail's recipient as sent."""
EMAIL_SATISFIED: Final = "satisfied"
"""Whether this e-mail on its own completes the task."""
EMAIL_REASON: Final = "reason"
"""Why the e-mail does not complete the task, or None when it does."""
