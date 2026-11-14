# SPDX-License-Identifier: Apache-2.0
"""Registration: the task is discoverable by name through the `probo` entry point."""

from importlib.metadata import entry_points
from pathlib import Path

from probo.scenarios.helpdesk_exfil.keys import META_SCENARIO, SCENARIO_ID

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
    assert log.eval.metadata == {META_SCENARIO: SCENARIO_ID}
