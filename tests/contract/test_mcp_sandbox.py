# SPDX-License-Identifier: Apache-2.0
"""Contract: an MCP server launched inside the Docker sandbox serves the host model loop."""

import socket
from pathlib import Path

import pytest
from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.model import ChatMessageTool, ModelOutput
from inspect_ai.scorer import Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import TaskState
from inspect_ai.tool import mcp_server_sandbox, mcp_tools
from inspect_ai.util import sandbox

from .fixtures.support import FIXTURES, MOCK_MODEL, run_docker_eval, samples

pytestmark = pytest.mark.docker


@scorer(metrics=[accuracy()])
def container_hostname() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        result = await sandbox().exec(["hostname"])
        injected = await sandbox().exec(
            ["sh", "-c", "stat -c %u /var/tmp/.*-v*/inspect-sandbox-tools"]
        )
        return Score(
            value=1,
            answer=result.stdout.strip(),
            metadata={"injected_tools_owner": injected.stdout.strip()},
        )

    return score


def test_sandbox_mcp_server_tools_callable_from_host_loop(tmp_path: Path) -> None:
    """mcp_server_sandbox runs the server in the container, even with network_mode: none.

    Inspect injects its own inspect-sandbox-tools binary (owned by root) to carry
    the MCP traffic, so the image only needs the server's own runtime.
    """
    server = mcp_server_sandbox(
        name="in-sandbox", command="python3", args=["/opt/probo/stdlib_server.py"]
    )
    task = Task(
        dataset=[Sample(input="where are you?")],
        solver=react(tools=[mcp_tools(server)]),
        scorer=container_hostname(),
        sandbox=("docker", str(FIXTURES / "compose" / "mcp.yaml")),
    )
    outputs = [
        ModelOutput.for_tool_call(MOCK_MODEL, "sandbox_hostname", {}),
        ModelOutput.for_tool_call(MOCK_MODEL, "submit", {"answer": "done"}),
    ]
    (sample,) = samples(run_docker_eval(task, tmp_path, outputs))

    assert sample.scores is not None
    score = sample.scores["container_hostname"]
    container = score.answer
    tool_messages = [m for m in sample.messages if isinstance(m, ChatMessageTool)]
    assert [m.text for m in tool_messages] == [container]
    assert container != socket.gethostname()
    assert score.metadata == {"injected_tools_owner": "0"}
