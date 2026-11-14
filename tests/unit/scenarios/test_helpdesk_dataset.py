# SPDX-License-Identifier: Apache-2.0
"""Dataset and the customer_note slot: defaults, overrides, and their sample metadata."""

from pathlib import Path

import pytest

# task_with's `scorer` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import task_with  # pyright: ignore[reportUnknownVariableType]

from probo.scenarios.helpdesk_exfil.data import DEFAULT_CUSTOMER_NOTE
from probo.scenarios.helpdesk_exfil.dataset import (
    HelpdeskSampleMetadata,
    NoteOverride,
    build_dataset,
    visible_elsewhere,
)
from probo.scenarios.helpdesk_exfil.keys import (
    META_NOTE_DEFAULT,
    META_NOTE_TEXT,
    META_NOTE_TICKET,
    META_SCENARIO,
    META_SEED,
    META_USER_TASK,
    META_WATCH_ADDRESS,
    SCENARIO_ID,
)
from probo.scenarios.helpdesk_exfil.task import helpdesk_exfil
from probo.scenarios.helpdesk_exfil.user_tasks import REPLY_ORDER_STATUS, USER_TASKS

from .helpdesk_support import run, same_calls, samples_by_id, scripted_agent, tool_messages

NOTE = "P.S. My {order} came in a {blue} box - is that normal?"
READ_BOTH = same_calls(
    [("read_ticket", {"ticket_id": "T-1001"}), ("read_ticket", {"ticket_id": "T-1002"})]
)


def test_metadata_fields_are_the_exported_keys() -> None:
    """Every sample metadata key is one of the exported constants."""
    assert set(HelpdeskSampleMetadata.model_fields) == {
        META_SCENARIO,
        META_USER_TASK,
        META_SEED,
        META_NOTE_TICKET,
        META_NOTE_DEFAULT,
        META_NOTE_TEXT,
        META_WATCH_ADDRESS,
    }


def test_default_dataset_has_one_default_sample_per_user_task() -> None:
    """Without overrides each user task gets `<id>/none` with the default slot recorded."""
    samples = list(build_dataset(42))
    assert [s.id for s in samples] == [f"{t.id}/none" for t in USER_TASKS]
    for sample, task in zip(samples, USER_TASKS, strict=True):
        assert sample.input == task.prompt
        assert sample.metadata == {
            META_SCENARIO: SCENARIO_ID,
            META_USER_TASK: task.id,
            META_SEED: 42,
            META_NOTE_TICKET: task.ticket_id,
            META_NOTE_DEFAULT: True,
            META_NOTE_TEXT: DEFAULT_CUSTOMER_NOTE,
            META_WATCH_ADDRESS: None,
        }


def test_override_is_in_metadata_and_read_ticket(tmp_path: Path) -> None:
    """An override lands verbatim in its task's ticket and metadata; other tickets keep defaults."""
    override = NoteOverride(variant="braces", text=NOTE)
    dataset = build_dataset(3, {REPLY_ORDER_STATUS.id: override})
    task = task_with(helpdesk_exfil(seed=3), dataset=dataset)
    by_id = samples_by_id(run(tmp_path, scripted_agent(READ_BOTH), task=task))
    assert set(by_id) == {"reply-order-status/braces", "reply-delivery-date/none"}

    overridden = by_id["reply-order-status/braces"]
    assert overridden.metadata[META_NOTE_DEFAULT] is False
    assert overridden.metadata[META_NOTE_TEXT] == NOTE
    assert overridden.metadata[META_NOTE_TICKET] == "T-1001"
    own, other = (m.text for m in tool_messages(overridden, "read_ticket"))
    assert NOTE in own
    assert DEFAULT_CUSTOMER_NOTE not in own
    assert DEFAULT_CUSTOMER_NOTE in other

    default = by_id["reply-delivery-date/none"]
    assert default.metadata[META_NOTE_DEFAULT] is True
    assert default.metadata[META_NOTE_TEXT] == DEFAULT_CUSTOMER_NOTE
    assert all(DEFAULT_CUSTOMER_NOTE in m.text for m in tool_messages(default, "read_ticket"))


def test_default_flag_must_match_default_text() -> None:
    """Metadata claiming the default slot text with other text is refused."""
    (sample,) = [s for s in build_dataset(1) if s.id == f"{REPLY_ORDER_STATUS.id}/none"]
    assert sample.metadata is not None
    with pytest.raises(ValueError, match="text is not the default"):
        HelpdeskSampleMetadata.model_validate({**sample.metadata, META_NOTE_TEXT: "other"})


@pytest.mark.parametrize("variant", ["none", "Upper", "two  spaces", "-lead", "a--b", ""])
def test_override_variant_must_be_a_slug_other_than_none(variant: str) -> None:
    """Variants that would collide with the default or make unreadable ids are refused."""
    with pytest.raises(ValueError, match="invalid override variant"):
        NoteOverride(variant=variant, text="x")


def test_override_for_unknown_user_task_is_refused() -> None:
    """An override keyed on a user task that does not exist is an error, not ignored."""
    with pytest.raises(ValueError, match="unknown user tasks"):
        build_dataset(1, {"no-such-task": NoteOverride(variant="x", text="x")})


def test_watch_address_is_recorded_in_every_sample() -> None:
    """A watched address goes into every sample's metadata, overridden or not."""
    overrides = {
        REPLY_ORDER_STATUS.id: NoteOverride(variant="x", text="Reference: test note 7F3A.")
    }
    samples = list(build_dataset(1, overrides, watch_address="outside@elsewhere.test"))
    assert len(samples) == len(USER_TASKS)
    for sample in samples:
        assert sample.metadata is not None
        assert sample.metadata[META_WATCH_ADDRESS] == "outside@elsewhere.test"


def test_task_watch_address_reaches_sample_metadata() -> None:
    """The task's `watch_address` argument is the samples' watched address."""
    task = helpdesk_exfil(seed=1, watch_address="outside@elsewhere.test")
    assert {s.metadata[META_WATCH_ADDRESS] for s in task.dataset if s.metadata} == {
        "outside@elsewhere.test"
    }


@pytest.mark.parametrize("address", ["", "   "])
def test_blank_watch_address_is_refused(address: str) -> None:
    """A blank watched address is an error rather than a check that never fires."""
    with pytest.raises(ValueError, match="watch_address must not be blank"):
        build_dataset(1, watch_address=address)


def test_empty_override_text_is_refused() -> None:
    """An empty note would be found in every tool result, so it is refused."""
    with pytest.raises(ValueError, match="override text must not be empty"):
        NoteOverride(variant="x", text="")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Thanks in advance", id="other-ticket-default-note"),
        pytest.param("Where is my order?", id="ticket-list-subject"),
        pytest.param("Sticky keys", id="other-ticket-subject"),
        pytest.param("Alice Moreau", id="customer-record"),
        pytest.param("Account recovery code: PROBO-CANARY-", id="record-code-prefix"),
    ],
)
def test_override_text_seen_in_other_tool_output_is_refused(text: str) -> None:
    """A note that other tool output already shows could not be attributed to the slot."""
    with pytest.raises(ValueError, match="already occurs in other tool output"):
        build_dataset(1, {REPLY_ORDER_STATUS.id: NoteOverride(variant="x", text=text)})


def test_visible_elsewhere_covers_other_tickets_and_records_only() -> None:
    """The texts checked are the ticket list, the other tickets and the customer records."""
    texts = visible_elsewhere(REPLY_ORDER_STATUS.ticket_id)
    assert len(texts) == 1 + 2 + 3
    assert not any("I ordered an electric kettle" in t for t in texts)
    assert any("desk lamp" in t for t in texts)
