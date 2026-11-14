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

from probo.scenarios.helpdesk_exfil.data import DEFAULT_CUSTOMER_NOTE
from probo.scenarios.helpdesk_exfil.keys import SCENARIO_ID, TASK_NAME
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


class HelpdeskSampleMetadata(BaseModel):
    """Sample metadata. Field names are the metadata keys exported from `keys`."""

    model_config = ConfigDict(frozen=True)

    scenario: str
    user_task: str
    seed: int
    customer_note_ticket: str
    customer_note_default: bool
    customer_note_text: str | None

    @model_validator(mode="after")
    def _text_matches_default_flag(self) -> "HelpdeskSampleMetadata":
        if self.customer_note_default != (self.customer_note_text is None):
            raise ValueError("customer_note_text must be set exactly when the default is not used")
        return self

    def customer_note(self) -> str:
        """The text the `customer_note` slot holds in this sample."""
        if self.customer_note_text is None:
            return DEFAULT_CUSTOMER_NOTE
        return self.customer_note_text


def build_sample(task: UserTask, seed: int, override: NoteOverride | None = None) -> Sample:
    """A sample for one user task; `override` replaces the slot text in that task's ticket."""
    metadata = HelpdeskSampleMetadata(
        scenario=SCENARIO_ID,
        user_task=task.id,
        seed=seed,
        customer_note_ticket=task.ticket_id,
        customer_note_default=override is None,
        customer_note_text=None if override is None else override.text,
    )
    variant = DEFAULT_VARIANT if override is None else override.variant
    return Sample(
        id=f"{task.id}/{variant}",
        input=task.prompt,
        metadata=metadata.model_dump(),
    )


def build_dataset(seed: int, overrides: Mapping[str, NoteOverride] | None = None) -> MemoryDataset:
    """One sample per user task; `overrides` maps a user task id to its slot override.

    Raises:
        ValueError: If `overrides` names a user task that does not exist.
    """
    overrides = overrides or {}
    unknown = set(overrides) - {task.id for task in USER_TASKS}
    if unknown:
        raise ValueError(f"overrides name unknown user tasks: {sorted(unknown)}")
    samples = [build_sample(task, seed, overrides.get(task.id)) for task in USER_TASKS]
    return MemoryDataset(samples, name=TASK_NAME)
