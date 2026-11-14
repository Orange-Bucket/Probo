# SPDX-License-Identifier: Apache-2.0
"""Registration: the task is discoverable by name through the `probo` entry point."""

from importlib.metadata import entry_points
from pathlib import Path

import pytest
from inspect_ai.util import registry_create, registry_info

from probo.attacks import Corpus
from probo.scenarios.helpdesk_exfil.keys import (
    META_CORPUS_HASH,
    META_CORPUS_VERSION,
    META_SCENARIO,
    SCENARIO_ID,
    SCORER_NOTE_DELIVERED,
    SCORER_RECORD_LEAKED,
    SCORER_SENT_TO_WATCHED,
    SCORER_TASK_COMPLETED,
)

from .helpdesk_support import REGISTERED_TASK, run


def test_entry_point_names_the_registry_module() -> None:
    """The installed package declares the `inspect_ai` entry point `probo`."""
    (entry,) = entry_points(group="inspect_ai", name="probo")
    assert entry.value == "probo._registry"


def test_task_runs_by_registered_name(tmp_path: Path) -> None:
    """`probo/helpdesk_exfil` resolves to the task and accepts task args."""
    log = run(tmp_path, task=REGISTERED_TASK, task_args={"seed": 9})
    assert log.eval.task == REGISTERED_TASK
    assert log.eval.task_args["seed"] == 9  # the task parameter name, not a metadata key
    empty = Corpus(version="2026-11", family="static", templates=())
    assert log.eval.metadata == {
        META_SCENARIO: SCENARIO_ID,
        META_CORPUS_VERSION: "2026-11",
        META_CORPUS_HASH: empty.content_hash,
    }


@pytest.mark.parametrize(
    "name",
    [SCORER_TASK_COMPLETED, SCORER_RECORD_LEAKED, SCORER_SENT_TO_WATCHED, SCORER_NOTE_DELIVERED],
)
def test_scorers_resolve_by_registered_name(name: str) -> None:
    """Each scorer is registered as `probo/<name>`, so it can be named for rescoring."""
    scorer = registry_create("scorer", f"probo/{name}")
    assert registry_info(scorer).name == f"probo/{name}"
