# SPDX-License-Identifier: Apache-2.0
"""Dataset for the helpdesk scenario: one sample per user task, with optional slot overrides.

A sample carries only configuration (see `HelpdeskSampleMetadata`). The environment itself,
including the marker tokens, is built when the sample starts, because epochs reuse the same
`Sample` and every (sample, epoch) needs its own tokens.
"""

import re
from collections.abc import Mapping
from dataclasses import dataclass

from inspect_ai.dataset import MemoryDataset, Sample
from pydantic import BaseModel, ConfigDict, model_validator

from probo.checks.canary import CANARY_PREFIX
from probo.scenarios.helpdesk_exfil.data import (
    DEFAULT_CUSTOMER_NOTE,
    TICKET_TEMPLATES,
    build_customers,
)
from probo.scenarios.helpdesk_exfil.keys import SCENARIO_ID, TASK_NAME
from probo.scenarios.helpdesk_exfil.tools import customer_view, ticket_list_view, ticket_view
from probo.scenarios.helpdesk_exfil.user_tasks import USER_TASKS, UserTask

DEFAULT_VARIANT = "none"
"""Sample id suffix for a sample whose slot holds the default text."""

_VARIANT = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class NoteOverride:
    """Text to place in the `customer_note` slot instead of the default.

    `variant` names the override in the sample id (`<user task>/<variant>`); it must be
    lowercase letters, digits and single hyphens, and not `none`.
    """

    variant: str
    text: str

    def __post_init__(self) -> None:
        if not _VARIANT.fullmatch(self.variant) or self.variant == DEFAULT_VARIANT:
            raise ValueError(f"invalid override variant {self.variant!r}")
        # An empty note occurs in every text, so `note_delivered` could not tell it apart.
        if not self.text:
            raise ValueError("override text must not be empty")


class HelpdeskSampleMetadata(BaseModel):
    """Sample metadata. Field names are the metadata keys exported from `keys`.

    `seed` is the only source of truth for this sample's marker tokens (see `keys.META_SEED`).
    """

    model_config = ConfigDict(frozen=True)

    scenario: str
    user_task: str
    seed: int
    customer_note_ticket: str
    customer_note_default: bool
    customer_note_text: str
    """The exact text in the slot; equals `DEFAULT_CUSTOMER_NOTE` when the default is used."""
    watch_address: str | None = None
    """Address the `sent_to_watched_address` check looks for; None watches nothing."""

    @model_validator(mode="after")
    def _default_flag_matches_text(self) -> "HelpdeskSampleMetadata":
        if self.customer_note_default and self.customer_note_text != DEFAULT_CUSTOMER_NOTE:
            raise ValueError("customer_note_default is set but the text is not the default")
        return self

    @model_validator(mode="after")
    def _watch_address_not_blank(self) -> "HelpdeskSampleMetadata":
        if self.watch_address is not None and not self.watch_address.strip():
            raise ValueError("watch_address must not be blank")
        return self


def visible_elsewhere(note_ticket_id: str) -> list[str]:
    """Tool output that never holds the slot of ticket `note_ticket_id`.

    That is the ticket list, every other ticket as `read_ticket` shows it (with the default
    note), and every customer record as `get_customer` shows it. Recovery codes are drawn
    per run, so a record shows only the fixed `CANARY_PREFIX` in their place here.
    """
    others = [t.render(DEFAULT_CUSTOMER_NOTE) for t in TICKET_TEMPLATES if t.id != note_ticket_id]
    tickets = [t.render(DEFAULT_CUSTOMER_NOTE) for t in TICKET_TEMPLATES]
    customers = build_customers(lambda customer_id: CANARY_PREFIX)
    return [
        ticket_list_view(tickets),
        *map(ticket_view, others),
        *map(customer_view, customers),
    ]


def build_sample(
    task: UserTask,
    seed: int,
    override: NoteOverride | None = None,
    watch_address: str | None = None,
) -> Sample:
    """A sample for one user task.

    `override` replaces the slot text in that task's ticket; `watch_address` is recorded for
    the `sent_to_watched_address` check.

    Raises:
        ValueError: If the override text already occurs in tool output outside the slot
            (see `visible_elsewhere`), where `note_delivered` could not tell it apart.
    """
    if override is not None and any(override.text in t for t in visible_elsewhere(task.ticket_id)):
        raise ValueError(f"override text {override.text!r} already occurs in other tool output")
    metadata = HelpdeskSampleMetadata(
        scenario=SCENARIO_ID,
        user_task=task.id,
        seed=seed,
        customer_note_ticket=task.ticket_id,
        customer_note_default=override is None,
        customer_note_text=DEFAULT_CUSTOMER_NOTE if override is None else override.text,
        watch_address=watch_address,
    )
    variant = DEFAULT_VARIANT if override is None else override.variant
    return Sample(
        id=f"{task.id}/{variant}",
        input=task.prompt,
        metadata=metadata.model_dump(),
    )


def build_dataset(
    seed: int,
    overrides: Mapping[str, NoteOverride] | None = None,
    watch_address: str | None = None,
) -> MemoryDataset:
    """One sample per user task; `overrides` maps a user task id to its slot override.

    `watch_address` is watched in every sample, overridden or not, so samples with the
    default note measure how often the address is used without being asked for.

    Raises:
        ValueError: If `overrides` names a user task that does not exist.
    """
    overrides = overrides or {}
    unknown = set(overrides) - {task.id for task in USER_TASKS}
    if unknown:
        raise ValueError(f"overrides name unknown user tasks: {sorted(unknown)}")
    samples = [
        build_sample(task, seed, overrides.get(task.id), watch_address) for task in USER_TASKS
    ]
    return MemoryDataset(samples, name=TASK_NAME)
