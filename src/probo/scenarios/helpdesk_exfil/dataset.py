# SPDX-License-Identifier: Apache-2.0
"""Dataset for the helpdesk scenario: user tasks crossed with `customer_note` variants.

With a template corpus, every user task gets a control sample (the default note) and one
sample per selected template, whose note is the template rendered with the values in
`placeholder_values`. Without a corpus there is one sample per user task, and tests can
override single notes directly.

A sample carries only configuration (see `HelpdeskSampleMetadata`). The environment itself,
including the marker tokens, is built when the sample starts, because epochs reuse the same
`Sample` and every (sample, epoch) needs its own tokens.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from inspect_ai.dataset import MemoryDataset, Sample
from pydantic import BaseModel, ConfigDict, model_validator

from probo.attacks import Corpus, Template
from probo.checks.canary import CANARY_PREFIX
from probo.scenarios.helpdesk_exfil.data import (
    COMPANY,
    DEFAULT_CUSTOMER_NOTE,
    SUPPORT_ADDRESS,
    TICKET_TEMPLATES,
    build_customers,
)
from probo.scenarios.helpdesk_exfil.environment import Customer
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
    target_customer_id: str
    """The customer other than the ticket's author that templates refer to (`target_customer`)."""
    template_id: str | None = None
    """Id of the template rendered into the slot; None for a control or a direct override."""
    template_family: str | None = None
    """Family of that template; None when `template_id` is."""
    corpus_version: str | None = None
    """Version of the corpus the dataset was built from; None when no corpus was used."""
    corpus_content_hash: str | None = None
    """`Corpus.content_hash` of that corpus; None when no corpus was used."""

    @model_validator(mode="after")
    def _default_flag_matches_text(self) -> "HelpdeskSampleMetadata":
        if self.customer_note_default and self.customer_note_text != DEFAULT_CUSTOMER_NOTE:
            raise ValueError("customer_note_default is set but the text is not the default")
        return self

    @model_validator(mode="after")
    def _template_fields_agree(self) -> "HelpdeskSampleMetadata":
        if (self.template_id is None) != (self.template_family is None):
            raise ValueError("template_id and template_family must be set together")
        if (self.corpus_version is None) != (self.corpus_content_hash is None):
            raise ValueError("corpus_version and corpus_content_hash must be set together")
        if self.template_id is not None and self.corpus_version is None:
            raise ValueError("a template sample must record its corpus")
        if self.template_id is not None and self.customer_note_default:
            raise ValueError("a template sample cannot hold the default note")
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


PLACEHOLDERS: Final = (
    "author_customer_id",
    "author_customer_name",
    "company",
    "support_address",
    "target_customer_email",
    "target_customer_id",
    "target_customer_name",
    "ticket_id",
    "watch_address",
)
"""Every placeholder a template may use in this scenario; see `placeholder_values`."""


def _customers() -> list[Customer]:
    return build_customers(lambda customer_id: CANARY_PREFIX)


def author_customer(task: UserTask) -> Customer:
    """The customer who wrote the ticket `task` works on."""
    author_id = next(t.customer_id for t in TICKET_TEMPLATES if t.id == task.ticket_id)
    return next(c for c in _customers() if c.id == author_id)


def target_customer(task: UserTask) -> Customer:
    """The customer templates refer to: the one after the ticket's author in the fixed
    customer order, wrapping round, so it is never the author."""
    customers = _customers()
    position = [c.id for c in customers].index(author_customer(task).id)
    return customers[(position + 1) % len(customers)]


def placeholder_values(task: UserTask, watch_address: str | None) -> dict[str, str]:
    """The value of each placeholder for `task`.

    - `ticket_id`: the ticket the task works on.
    - `author_customer_id`, `author_customer_name`: that ticket's author.
    - `target_customer_id`, `target_customer_name`, `target_customer_email`: see
      `target_customer`.
    - `company`, `support_address`: the fictional shop and its helpdesk mailbox.
    - `watch_address`: the sample's watched address; absent when nothing is watched.
    """
    author, target = author_customer(task), target_customer(task)
    values = {
        "author_customer_id": author.id,
        "author_customer_name": author.name,
        "company": COMPANY,
        "support_address": SUPPORT_ADDRESS,
        "target_customer_email": target.email,
        "target_customer_id": target.id,
        "target_customer_name": target.name,
        "ticket_id": task.ticket_id,
    }
    if watch_address is not None:
        values["watch_address"] = watch_address
    return values


def render_template(template: Template, task: UserTask, watch_address: str | None) -> str:
    """`template` rendered with the scenario's values for `task`.

    Raises:
        ValueError: If the template uses a placeholder this scenario does not supply, or
            uses `watch_address` when nothing is watched.
    """
    values = placeholder_values(task, watch_address)
    unknown = sorted(set(template.placeholders) - set(PLACEHOLDERS))
    if unknown:
        raise ValueError(
            f"template {template.id!r} uses placeholders this scenario does not supply: "
            f"{unknown}; supplied: {list(PLACEHOLDERS)}"
        )
    if "watch_address" in template.placeholders and watch_address is None:
        raise ValueError(f"template {template.id!r} uses watch_address but nothing is watched")
    return template.render({name: values[name] for name in template.placeholders})


def build_sample(
    task: UserTask,
    seed: int,
    override: NoteOverride | None = None,
    watch_address: str | None = None,
    *,
    template: Template | None = None,
    corpus: Corpus | None = None,
) -> Sample:
    """A sample for one user task.

    The slot of that task's ticket holds the default note, or `override`'s text, or
    `template` rendered by `render_template` (the sample id then ends in the template id).
    `watch_address` is recorded for the `sent_to_watched_address` check, and `corpus` for
    the corpus version and content hash.

    Raises:
        ValueError: If both `override` and `template` are given, if `template` is given
            without `corpus`, if the template cannot be rendered, or if the slot text
            already occurs in tool output outside the slot (see `visible_elsewhere`), where
            `note_delivered` could not tell it apart.
    """
    if template is not None:
        if override is not None:
            raise ValueError("give either an override or a template, not both")
        if corpus is None:
            raise ValueError("a template sample needs the corpus it came from")
        override = NoteOverride(
            variant=template.id, text=render_template(template, task, watch_address)
        )
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
        target_customer_id=target_customer(task).id,
        template_id=None if template is None else template.id,
        template_family=None if template is None else template.family,
        corpus_version=None if corpus is None else corpus.version,
        corpus_content_hash=None if corpus is None else corpus.content_hash,
    )
    variant = DEFAULT_VARIANT if override is None else override.variant
    return Sample(
        id=f"{task.id}/{variant}",
        input=task.prompt,
        metadata=metadata.model_dump(),
    )


def select_templates(corpus: Corpus, templates: Sequence[str] | None) -> tuple[Template, ...]:
    """The corpus templates named in `templates` (all when None), in corpus (id) order.

    Raises:
        ValueError: If `templates` names an id the corpus does not hold.
    """
    if templates is None:
        return corpus.templates
    unknown = sorted(set(templates) - set(corpus.ids))
    if unknown:
        raise ValueError(f"unknown template ids {unknown}; the corpus holds {list(corpus.ids)}")
    return tuple(t for t in corpus.templates if t.id in set(templates))


def build_dataset(
    seed: int,
    overrides: Mapping[str, NoteOverride] | None = None,
    watch_address: str | None = None,
    *,
    corpus: Corpus | None = None,
    templates: Sequence[str] | None = None,
) -> MemoryDataset:
    """The scenario's samples, in user task order.

    With `corpus`: for each user task, a control sample `<user task>/none` followed by one
    sample `<user task>/<template id>` per selected template (`select_templates`). A corpus
    without templates gives the control samples only.

    Without `corpus`: one sample per user task; `overrides` maps a user task id to a direct
    slot override, which is how tests place arbitrary text in a ticket.

    `watch_address` is watched in every sample, control or not, so control samples measure
    how often the address is used without being asked for.

    Raises:
        ValueError: If `overrides` is combined with `corpus`, names a user task that does
            not exist, or `templates` is given without `corpus` or names an unknown id.
    """
    overrides = overrides or {}
    if corpus is not None:
        if overrides:
            raise ValueError("overrides cannot be combined with a corpus")
        selected = select_templates(corpus, templates)
        samples = [
            build_sample(task, seed, None, watch_address, template=template, corpus=corpus)
            for task in USER_TASKS
            for template in (None, *selected)
        ]
        return MemoryDataset(samples, name=TASK_NAME)
    if templates is not None:
        raise ValueError("templates were selected but no corpus was given")
    unknown = set(overrides) - {task.id for task in USER_TASKS}
    if unknown:
        raise ValueError(f"overrides name unknown user tasks: {sorted(unknown)}")
    samples = [
        build_sample(task, seed, overrides.get(task.id), watch_address) for task in USER_TASKS
    ]
    return MemoryDataset(samples, name=TASK_NAME)
