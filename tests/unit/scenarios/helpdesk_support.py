# SPDX-License-Identifier: Apache-2.0
"""Test helpers for the helpdesk scenario: scripted mockllm agents and quiet eval runs."""

from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from inspect_ai import Task

# eval's `scanner` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import eval as inspect_eval  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.log import EvalLog, EvalSample
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score
from inspect_ai.tool import ToolChoice, ToolInfo

from probo.scenarios.helpdesk_exfil.keys import SCORER_TASK_COMPLETED, TASK_NAME

MOCK_MODEL = "mockllm/model"
REGISTERED_TASK = f"probo/{TASK_NAME}"

Call = tuple[str, dict[str, Any]]
"""A tool call the scripted agent makes: tool name and arguments."""
Plan = Callable[[str], Sequence[Call]]
"""Maps the user prompt of a sample to the tool calls the agent makes, in order."""


def scripted_agent(plan: Plan) -> Model:
    """A mockllm model that makes `plan(prompt)`'s calls in order, then calls submit.

    The step is the number of assistant messages already in the conversation, so the script
    is keyed on each sample's own conversation and works across samples and epochs.
    """

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        prompt = next(m for m in messages if isinstance(m, ChatMessageUser)).text
        steps = [*plan(prompt), ("submit", {"answer": "done"})]
        step = sum(isinstance(m, ChatMessageAssistant) for m in messages)
        if step >= len(steps):
            return ModelOutput.from_content(MOCK_MODEL, "done")
        name, arguments = steps[step]
        return ModelOutput.for_tool_call(MOCK_MODEL, name, arguments)

    return get_model(MOCK_MODEL, custom_outputs=output)


def same_calls(calls: Sequence[Call]) -> Plan:
    """A plan making the same calls in every sample."""
    return lambda prompt: calls


def run(
    tmp_path: Path,
    model: Model | None = None,
    task: Task | str = REGISTERED_TASK,
    task_args: Mapping[str, Any] | None = None,
    **eval_args: Any,
) -> EvalLog:
    """Run the helpdesk task (by registered name unless `task` is given) quietly."""
    logs = inspect_eval(
        task,
        model=model or get_model(MOCK_MODEL),
        task_args=dict(task_args or {}),
        log_dir=str(tmp_path),
        display="none",
        **eval_args,
    )
    assert len(logs) == 1
    log = logs[0]
    assert log.status == "success", log.error
    return log


def samples_by_id(log: EvalLog) -> dict[str, EvalSample]:
    """Samples of a single-epoch log keyed by sample id."""
    assert log.samples is not None
    assert all(s.epoch == 1 for s in log.samples)
    return {str(s.id): s for s in log.samples}


def completed(sample: EvalSample) -> Score:
    """The sample's `task_completed` score."""
    assert sample.error is None, sample.error
    assert sample.scores is not None
    return sample.scores[SCORER_TASK_COMPLETED]


def tool_messages(sample: EvalSample, function: str | None = None) -> list[ChatMessageTool]:
    """Tool result messages of a sample, optionally only those of one tool."""
    return [
        m
        for m in sample.messages
        if isinstance(m, ChatMessageTool) and (function is None or m.function == function)
    ]
