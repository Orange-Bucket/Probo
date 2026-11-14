# SPDX-License-Identifier: Apache-2.0
"""Contract: Inspect's MCP client against stdio servers built on the mcp 2.x SDK."""

import importlib
import sys
from pathlib import Path

import anyio
import pytest
from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample, resolve_sample_attachments
from inspect_ai.model import ChatMessageTool, ModelOutput
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import MCPServer, ToolInfo, mcp_server_stdio, mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool

from .fixtures.support import FIXTURES, MOCK_MODEL, run_eval, samples

SERVERS = FIXTURES / "mcp_servers"


def stdio_server(script: str) -> MCPServer:
    return mcp_server_stdio(name=script, command=sys.executable, args=[str(SERVERS / script)])


def call(tool: str, **arguments: str) -> ModelOutput:
    return ModelOutput.for_tool_call(MOCK_MODEL, tool, arguments)


def tool_results(sample: EvalSample) -> list[str]:
    return [m.text for m in sample.messages if isinstance(m, ChatMessageTool)]


def model_tools(sample: EvalSample) -> list[dict[str, ToolInfo]]:
    """Tool definitions sent to the model on each generate, keyed by name.

    Logged text over 100 characters is stored as an attachment:// reference.
    """
    resolved = resolve_sample_attachments(sample)
    events = [e for e in resolved.events if isinstance(e, ModelEvent)]
    return [{t.name: t for t in e.tools} for e in events]


async def sdk_list_tools(script: str) -> list[MCPTool]:
    """List a fixture server's tools with the raw mcp SDK client."""
    params = StdioServerParameters(command=sys.executable, args=[str(SERVERS / script)])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        return (await session.list_tools()).tools


def test_mcp_2_sdk_server_api() -> None:
    """mcp 2.x removed mcp.server.fastmcp; FastMCP is now mcp.server.mcpserver.MCPServer."""
    with pytest.raises(ModuleNotFoundError, match="FastMCP was renamed to MCPServer"):
        importlib.import_module("mcp.server.fastmcp")
    assert importlib.import_module("mcp.server.mcpserver").MCPServer is not None


def test_react_agent_calls_stdio_mcp_tool(tmp_path: Path) -> None:
    """mcp_tools(mcp_server_stdio(...)) exposes server tools that a react loop can call."""
    task = Task(
        dataset=[Sample(input="forecast please")],
        solver=react(tools=[mcp_tools(stdio_server("benign_server.py"))]),
    )
    outputs = [call("get_forecast", city="Lisbon"), call("submit", answer="sunny")]
    (sample,) = samples(run_eval(task, tmp_path, outputs))

    assert tool_results(sample) == ["Forecast for Lisbon: sunny, 21C"]
    assert sample.output.completion.endswith("sunny")


def test_tool_descriptions_reach_model_verbatim(tmp_path: Path) -> None:
    """Tool and parameter descriptions in the ModelEvent equal what the server lists."""
    (listed,) = anyio.run(sdk_list_tools, "benign_server.py")
    task = Task(
        dataset=[Sample(input="x")],
        solver=react(tools=[mcp_tools(stdio_server("benign_server.py"))]),
    )
    (sample,) = samples(run_eval(task, tmp_path, [call("submit", answer="x")]))

    (tools,) = model_tools(sample)
    sent = tools["get_forecast"]
    assert listed.description is not None and "\n\n<note>" in listed.description
    assert sent.description == listed.description
    city = sent.parameters.properties["city"]
    assert city.description == listed.input_schema["properties"]["city"]["description"]


def test_missing_parameter_description_is_filled_with_its_name(tmp_path: Path) -> None:
    """Inspect replaces an absent MCP parameter description with the parameter name."""
    listed = {t.name: t for t in anyio.run(sdk_list_tools, "rugpull_server.py")}
    assert "description" not in listed["get_forecast"].input_schema["properties"]["city"]
    task = Task(
        dataset=[Sample(input="x")],
        solver=react(tools=[mcp_tools(stdio_server("rugpull_server.py"))]),
    )
    (sample,) = samples(run_eval(task, tmp_path, [call("submit", answer="x")]))

    (tools,) = model_tools(sample)
    assert tools["get_forecast"].parameters.properties["city"].description == "city"


def test_tool_list_is_cached_for_the_connection(tmp_path: Path) -> None:
    """A changed tool list (plus list_changed) never reaches the model within a sample."""
    task = Task(
        dataset=[Sample(input="x")],
        solver=react(tools=[mcp_tools(stdio_server("rugpull_server.py"))]),
    )
    outputs = [
        call("rug_pull"),
        call("get_forecast", city="Porto"),
        call("submit", answer="x"),
    ]
    (sample,) = samples(run_eval(task, tmp_path, outputs))

    assert tool_results(sample)[:2] == ["now at version 2", "forecast v2 for Porto"]
    descriptions = {tools["get_forecast"].description for tools in model_tools(sample)}
    assert descriptions == {"Forecast tool, description version 1."}


def test_each_sample_gets_a_fresh_server_process(tmp_path: Path) -> None:
    """Server state does not carry over between samples: each sample relaunches it."""
    task = Task(
        dataset=[Sample(input="a"), Sample(input="b")],
        solver=react(tools=[mcp_tools(stdio_server("rugpull_server.py"))]),
    )
    outputs = [call("rug_pull"), call("submit", answer="a")] * 2
    log = run_eval(task, tmp_path, outputs, max_samples=1)

    assert [tool_results(s)[0] for s in samples(log)] == ["now at version 2"] * 2


def test_plain_generate_relaunches_server_per_tool_call(tmp_path: Path) -> None:
    """Outside react() there is no mcp_connection, so every tool call gets a new process."""
    task = Task(
        dataset=[Sample(input="x")],
        solver=[use_tools(mcp_tools(stdio_server("rugpull_server.py"))), generate()],
    )
    outputs = [
        call("rug_pull"),
        call("get_forecast", city="Porto"),
        ModelOutput.from_content(MOCK_MODEL, "done"),
    ]
    (sample,) = samples(run_eval(task, tmp_path, outputs))

    assert tool_results(sample) == ["now at version 2", "forecast v1 for Porto"]
