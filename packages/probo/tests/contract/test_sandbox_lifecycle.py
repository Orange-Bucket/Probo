# SPDX-License-Identifier: Apache-2.0
"""Contract: Inspect's Docker sandbox lifecycle, access paths and compose rules."""

import os
import re
import socket
from pathlib import Path
from typing import Any

import pytest
from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog
from inspect_ai.model import ChatMessageTool, ModelOutput
from inspect_ai.scorer import Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import Generate, Solver, TaskState, generate, solver, use_tools
from inspect_ai.tool import Tool, tool
from inspect_ai.util import sandbox

from .fixtures.support import (
    FIXTURES,
    MOCK_MODEL,
    inspect_compose_projects,
    run_docker_eval,
    samples,
)

pytestmark = pytest.mark.docker

COMPOSE = FIXTURES / "compose"
MARKER = "/tmp/probo-marker"


def host_identity() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def score_metadata(log: EvalLog) -> list[dict[str, Any]]:
    """Metadata of the single score on each sample, in log order."""
    result: list[dict[str, Any]] = []
    for sample in samples(log):
        assert sample.scores is not None and len(sample.scores) == 1
        (score,) = sample.scores.values()
        assert score.metadata is not None
        result.append(score.metadata)
    return result


@solver
def leave_marker() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        seen = await sandbox().exec(["sh", "-c", f"cat {MARKER} 2>/dev/null || true"])
        state.metadata["marker_before"] = seen.stdout
        await sandbox().write_file(MARKER, f"{state.sample_id}/{state.epoch}")
        return state

    return solve


@scorer(metrics=[accuracy()])
def read_marker() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        hostname = await sandbox().exec(["hostname"])
        return Score(
            value=1,
            metadata={
                "marker_before": state.metadata["marker_before"],
                "marker_after": await sandbox().read_file(MARKER),
                "container": hostname.stdout.strip(),
            },
        )

    return score


@tool
def leave_note() -> Tool:
    async def execute(text: str) -> str:
        """Write a note into the sandbox and report where this tool ran.

        Args:
            text: Note to write.
        """
        await sandbox().write_file("/tmp/note.txt", text)
        return host_identity()

    return execute


@scorer(metrics=[accuracy()])
def read_note() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        container = await sandbox().exec(["hostname"])
        return Score(
            value=1,
            metadata={
                "note": await sandbox().read_file("/tmp/note.txt"),
                "container": container.stdout.strip(),
                "scorer_host": host_identity(),
            },
        )

    return score


@solver
def touch_both_services() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        await sandbox("peer").write_file("/tmp/peer-only.txt", "written via sandbox('peer')")
        return state

    return solve


@scorer(metrics=[accuracy()])
def read_both_services() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        default_sees = await sandbox().exec(["test", "-e", "/tmp/peer-only.txt"])
        return Score(
            value=1,
            metadata={
                "default_host": (await sandbox().exec(["hostname"])).stdout.strip(),
                "peer_host": (await sandbox("peer").exec(["hostname"])).stdout.strip(),
                "peer_file": await sandbox("peer").read_file("/tmp/peer-only.txt"),
                "default_has_peer_file": default_sees.success,
            },
        )

    return score


@solver
def probe_identity() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        uid = await sandbox().exec(["id", "-u"])
        cgroup_v2 = await sandbox().exec(["test", "-e", "/sys/fs/cgroup/cgroup.controllers"])
        limits = await sandbox().exec(
            ["cat", *(f"/sys/fs/cgroup/{name}" for name in ("memory.max", "cpu.max", "pids.max"))]
        )
        as_root = await sandbox().exec(["id", "-u"], user="root")
        await sandbox().write_file("/tmp/as-default-user.txt", "ok")
        owner = await sandbox().exec(["stat", "-c", "%u", "/tmp/as-default-user.txt"])
        state.metadata["uid"] = uid.stdout.strip()
        state.metadata["cgroup_v2"] = cgroup_v2.success
        state.metadata["limits"] = limits.stdout.splitlines()
        state.metadata["root_uid"] = as_root.stdout.strip()
        state.metadata["file_owner"] = owner.stdout.strip()
        return state

    return solve


def test_fresh_compose_project_per_sample_and_epoch(tmp_path: Path) -> None:
    """Each sample and each epoch gets its own containers; no state carries over."""
    task = Task(
        dataset=[Sample(input="a", id="a"), Sample(input="b", id="b")],
        solver=leave_marker(),
        scorer=read_marker(),
        sandbox=("docker", str(COMPOSE / "single.yaml")),
        epochs=2,
    )
    log = run_docker_eval(task, tmp_path, max_samples=1)

    runs = score_metadata(log)
    assert len(runs) == 4
    assert all(run["marker_before"] == "" for run in runs)
    assert len({run["container"] for run in runs}) == 4
    expected = {f"{s.id}/{s.epoch}" for s in samples(log)}
    assert {run["marker_after"] for run in runs} == expected


def test_tool_and_scorer_reach_sandbox_but_run_on_host(tmp_path: Path) -> None:
    """A @tool and a scorer use sandbox() while executing in the eval process."""
    task = Task(
        dataset=[Sample(input="leave a note")],
        solver=[use_tools(leave_note()), generate()],
        scorer=read_note(),
        sandbox=("docker", str(COMPOSE / "single.yaml")),
    )
    outputs = [
        ModelOutput.for_tool_call(MOCK_MODEL, "leave_note", {"text": "hello from the tool"}),
        ModelOutput.from_content(MOCK_MODEL, "done"),
    ]
    log = run_docker_eval(task, tmp_path, outputs)

    (sample,) = samples(log)
    (meta,) = score_metadata(log)
    tool_messages = [m for m in sample.messages if isinstance(m, ChatMessageTool)]
    assert [m.text for m in tool_messages] == [host_identity()]
    assert meta["scorer_host"] == host_identity()
    assert meta["note"] == "hello from the tool"
    assert meta["container"] != socket.gethostname()


def test_named_services_in_multi_service_compose(tmp_path: Path) -> None:
    """sandbox('name') addresses one service; files do not leak between services."""
    task = Task(
        dataset=[Sample(input="x")],
        solver=touch_both_services(),
        scorer=read_both_services(),
        sandbox=("docker", str(COMPOSE / "internal.yaml")),
    )
    (meta,) = score_metadata(run_docker_eval(task, tmp_path))

    assert meta["peer_file"] == "written via sandbox('peer')"
    assert meta["default_has_peer_file"] is False
    assert meta["default_host"] != meta["peer_host"]


def test_x_default_selects_default_service(tmp_path: Path) -> None:
    """Without a service named 'default', x-default: true picks sandbox()'s target."""

    @solver
    def write_on_default() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            await sandbox().write_file("/tmp/who", "default")
            other = await sandbox("helper").exec(["test", "-e", "/tmp/who"])
            state.metadata["helper_has_file"] = other.success
            return state

        return solve

    task = Task(
        dataset=[Sample(input="x")],
        solver=write_on_default(),
        sandbox=("docker", str(COMPOSE / "x_default.yaml")),
    )
    (sample,) = samples(run_docker_eval(task, tmp_path))
    assert sample.metadata["helper_has_file"] is False


@pytest.mark.parametrize(
    ("compose_file", "message"),
    [
        ("no_default.yaml", "No 'default' service found"),
        ("exits.yaml", "No services started"),
    ],
)
def test_compose_file_rejected(tmp_path: Path, compose_file: str, message: str) -> None:
    """A compose file needs a default service whose main process keeps running."""
    task = Task(dataset=[Sample(input="x")], sandbox=("docker", str(COMPOSE / compose_file)))
    log = run_docker_eval(task, tmp_path)

    assert log.status == "error"
    assert log.error is not None and message in log.error.message


def test_compose_user_and_resource_limits_apply(tmp_path: Path) -> None:
    """Compose 'user' sets the exec user; mem_limit, cpus and pids_limit reach cgroups."""
    task = Task(
        dataset=[Sample(input="x")],
        solver=probe_identity(),
        sandbox=("docker", str(COMPOSE / "limits.yaml")),
    )
    (sample,) = samples(run_docker_eval(task, tmp_path))

    assert sample.metadata["uid"] == "1000"
    assert sample.metadata["root_uid"] == "0"
    assert sample.metadata["file_owner"] == "1000"
    if not sample.metadata["cgroup_v2"]:
        pytest.skip("resource-limit checks read cgroup v2 files; this Docker host uses cgroup v1")
    assert sample.metadata["limits"] == [str(256 * 1024 * 1024), "50000 100000", "64"]


def test_default_user_is_image_user(tmp_path: Path) -> None:
    """Without a compose 'user', exec runs as the image's user (root for python:slim)."""

    @solver
    def whoami() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            state.metadata["uid"] = (await sandbox().exec(["id", "-u"])).stdout.strip()
            state.metadata["cwd"] = (await sandbox().exec(["pwd"])).stdout.strip()
            return state

        return solve

    task = Task(
        dataset=[Sample(input="x")],
        solver=whoami(),
        sandbox=("docker", str(COMPOSE / "single.yaml")),
    )
    (sample,) = samples(run_docker_eval(task, tmp_path))

    assert sample.metadata["uid"] == "0"
    assert sample.metadata["cwd"] == "/"


def test_compose_project_is_named_after_task(tmp_path: Path) -> None:
    """Sample projects are named inspect-<task[:12]>-i<id>, which run_docker_eval relies on."""

    @solver
    def record_projects() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            state.metadata["live"] = sorted(inspect_compose_projects("inspect-"))
            return state

        return solve

    task = Task(
        dataset=[Sample(input="x")],
        solver=record_projects(),
        sandbox=("docker", str(COMPOSE / "single.yaml")),
    )
    log = run_docker_eval(task, tmp_path)

    (sample,) = samples(log)
    assert re.fullmatch(r"probo-[0-9a-f]{6}", log.eval.task)
    ours = [p for p in sample.metadata["live"] if p.startswith(f"inspect-{log.eval.task}-i")]
    assert len(ours) == 1
