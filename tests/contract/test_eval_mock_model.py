# SPDX-License-Identifier: Apache-2.0
"""Contract: mockllm drives tool-calling agent loops from scripted outputs."""

import os
from pathlib import Path

import pytest
from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import Tool, ToolChoice, ToolInfo, tool
from inspect_ai.util import store

from .fixtures.support import MOCK_DEFAULT_OUTPUT, MOCK_MODEL, only_sample, run_eval


@tool
def lookup() -> Tool:
    async def execute(key: str) -> str:
        """Look up a key.

        Args:
            key: Key to look up.
        """
        store().set("looked_up", key)
        return f"value-for-{key}"

    return execute


def call_lookup_then_answer(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    last = messages[-1]
    if isinstance(last, ChatMessageTool):
        return ModelOutput.from_content(MOCK_MODEL, f"answer: {last.text}")
    return ModelOutput.for_tool_call(MOCK_MODEL, "lookup", {"key": "k1"}, tool_call_id="call-1")


def api_key_vars() -> list[str]:
    return sorted(var for var in os.environ if var.endswith("_API_KEY"))


def test_mockllm_runs_without_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """With no *_API_KEY variable set, mockllm/model completes and returns its default text.

    eval() loads a .env found above the cwd, so the run starts from tmp_path and the
    test checks that no key variable appeared during it.
    """
    for var in api_key_vars():
        monkeypatch.delenv(var)
    monkeypatch.chdir(tmp_path)
    log = run_eval(Task(dataset=[Sample(input="hi")], solver=[generate()]), tmp_path)
    assert api_key_vars() == []
    assert only_sample(log).output.completion == MOCK_DEFAULT_OUTPUT


def test_scripted_tool_call_drives_generate_loop(tmp_path: Path) -> None:
    """A callable custom_outputs can emit tool calls that generate() executes in-process."""
    task = Task(dataset=[Sample(input="go")], solver=[use_tools(lookup()), generate()])
    sample = only_sample(run_eval(task, tmp_path, call_lookup_then_answer))
    assert [m.role for m in sample.messages] == ["user", "assistant", "tool", "assistant"]
    call_message = sample.messages[1]
    assert isinstance(call_message, ChatMessageAssistant)
    assert call_message.tool_calls is not None
    assert call_message.tool_calls[0].function == "lookup"
    assert call_message.tool_calls[0].arguments == {"key": "k1"}
    tool_message = sample.messages[2]
    assert isinstance(tool_message, ChatMessageTool)
    assert tool_message.tool_call_id == "call-1"
    assert tool_message.text == "value-for-k1"
    assert sample.store["looked_up"] == "k1"
    assert sample.output.completion == "answer: value-for-k1"


def test_callable_custom_outputs_sees_offered_tools(tmp_path: Path) -> None:
    """The custom_outputs callable receives the ToolInfo list that the solver offered."""
    offered: list[list[str]] = []

    def record_tools(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        offered.append([t.name for t in tools])
        return ModelOutput.from_content(MOCK_MODEL, "no tools needed")

    task = Task(dataset=[Sample(input="go")], solver=[use_tools(lookup()), generate()])
    only_sample(run_eval(task, tmp_path, record_tools))
    assert offered == [["lookup"]]


def test_scripted_tool_call_drives_react_agent(tmp_path: Path) -> None:
    """react() offers a submit tool next to user tools and stops when the mock calls submit."""
    offered: list[str] = []

    def script(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        offered[:] = [t.name for t in tools]
        last = messages[-1]
        if isinstance(last, ChatMessageTool) and last.function == "lookup":
            return ModelOutput.for_tool_call(MOCK_MODEL, "submit", {"answer": last.text})
        return ModelOutput.for_tool_call(MOCK_MODEL, "lookup", {"key": "k2"})

    task = Task(dataset=[Sample(input="go")], solver=react(tools=[lookup()]))
    sample = only_sample(run_eval(task, tmp_path, script))
    assert sorted(offered) == ["lookup", "submit"]
    assert [m.role for m in sample.messages] == ["system", "user", "assistant", "tool", "assistant"]
    assert sample.store["looked_up"] == "k2"
    assert sample.output.completion.endswith("value-for-k2")


def test_exhausted_iterable_custom_outputs_errors_the_sample(tmp_path: Path) -> None:
    """An iterable custom_outputs that runs dry raises inside the sample instead of looping."""
    task = Task(dataset=[Sample(input="go")], solver=[use_tools(lookup()), generate()])
    outputs = [ModelOutput.for_tool_call(MOCK_MODEL, "lookup", {"key": "k"})]
    sample = only_sample(run_eval(task, tmp_path, outputs, fail_on_error=False))
    assert sample.error is not None
    assert "custom_outputs ran out of values" in sample.error.message
