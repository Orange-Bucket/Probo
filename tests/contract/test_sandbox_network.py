# SPDX-License-Identifier: Apache-2.0
"""Contract: which Docker sandbox configurations can reach the outside world."""

import importlib
import json
import socket
from pathlib import Path
from typing import Any

import pytest
import yaml
from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import sandbox

from .fixtures.support import FIXTURES, run_docker_eval, samples

COMPOSE = FIXTURES / "compose"
OUTSIDE = ("1.1.1.1", 443)

PROBE = """
import errno, json, socket, sys
def tcp(host, port):
    try:
        socket.create_connection((host, port), timeout=3).close()
        return "ok"
    except OSError as error:
        return errno.errorcode.get(error.errno or 0, type(error).__name__)
def default_route():
    with open("/proc/net/route") as table:
        return any(line.split()[1] == "00000000" for line in table.readlines()[1:])
print(json.dumps({
    "outside": tcp(sys.argv[1], int(sys.argv[2])),
    "peer": tcp("peer", 8000),
    "default_route": default_route(),
}))
"""


def host_is_online() -> bool:
    try:
        socket.create_connection(OUTSIDE, timeout=3).close()
    except OSError:
        return False
    return True


@solver
def probe_network() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        result = await sandbox().exec(["python3", "-c", PROBE, OUTSIDE[0], str(OUTSIDE[1])])
        assert result.success, result.stderr
        state.metadata.update(json.loads(result.stdout))
        return state

    return solve


def probe(tmp_path: Path, config: str | None) -> dict[str, Any]:
    """Run the network probe in a one-sample task and return what it saw."""
    spec = "docker" if config is None else ("docker", config)
    task = Task(dataset=[Sample(input="x")], solver=probe_network(), sandbox=spec)
    (sample,) = samples(run_docker_eval(task, tmp_path))
    return sample.metadata


def assert_cut_off(seen: dict[str, Any]) -> None:
    """Outside is unreachable, and not merely because the host is offline: no default route."""
    assert seen["outside"] != "ok"
    assert seen["default_route"] is False


def test_inspect_generic_auto_compose_sets_network_mode_none() -> None:
    """With no compose file or Dockerfile, Inspect's generated compose file is offline."""
    # Private module (a namespace package, so untyped): Inspect has no public accessor
    # for its generic auto-compose template.
    docker_config = importlib.import_module("inspect_ai.util._sandbox.docker.config")
    config = yaml.safe_load(docker_config.COMPOSE_GENERIC_YAML)
    assert config["services"]["default"]["network_mode"] == "none"


@pytest.mark.docker
def test_inspect_dockerfile_auto_compose_has_no_network(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bare Dockerfile under sandbox='docker' gets an offline auto-compose file.

    The file is generated outside the task directory, which is left untouched.
    """
    monkeypatch.chdir(FIXTURES / "default_sandbox")
    assert_cut_off(probe(tmp_path, None))
    assert list(Path.cwd().iterdir()) == [Path.cwd() / "Dockerfile"]


@pytest.mark.docker
def test_custom_compose_replaces_default_restriction(tmp_path: Path) -> None:
    """A compose file without network keys gets outbound access; nothing restates none."""
    if not host_is_online():
        pytest.skip(f"host cannot reach {OUTSIDE[0]}:{OUTSIDE[1]}")
    seen = probe(tmp_path, str(COMPOSE / "open.yaml"))
    assert seen["outside"] == "ok"


@pytest.mark.docker
def test_internal_network_allows_peers_only(tmp_path: Path) -> None:
    """A network marked internal: true connects services but has no outbound route."""
    seen = probe(tmp_path, str(COMPOSE / "internal.yaml"))
    assert seen["peer"] == "ok"
    assert_cut_off(seen)


@pytest.mark.docker
def test_network_mode_none_is_offline(tmp_path: Path) -> None:
    """network_mode: none in a custom compose file restores the default isolation."""
    assert_cut_off(probe(tmp_path, str(COMPOSE / "single.yaml")))
