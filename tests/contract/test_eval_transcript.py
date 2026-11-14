# SPDX-License-Identifier: Apache-2.0
"""Contract: a scorer reads the sample's events so far through `transcript().events`.

`probo.judges.reply_only` finds the final reply in the tool and model events a scorer sees
(also when a stored log is re-scored) and records the judge call's config from its model
event. `probo.scenarios.helpdesk_exfil.leak_checks.note_delivered` reads the same model
events.
"""

from pathlib import Path

# score's `scorers` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import (
    Task,
    score,  # pyright: ignore[reportUnknownVariableType]
)
from inspect_ai.dataset import Sample
from inspect_ai.event import Event, ModelEvent, ToolEvent
from inspect_ai.log import read_eval_log, transcript
from inspect_ai.model import (
    ChatMessage,
    ChatMessageTool,
    GenerateConfig,
    ModelOutput,
    get_model,
)
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState, generate, use_tools
from inspect_ai.tool import Tool, ToolChoice, ToolError, ToolInfo, tool

from .fixtures.support import MOCK_MODEL, ScorerView, only_sample, record_view, run_eval

ROLE_CONFIG = GenerateConfig(temperature=0.7, top_p=0.9, max_tokens=50)
CALL_CONFIG = GenerateConfig(temperature=0.0, max_tokens=1024)


@tool
def echo() -> Tool:
    async def execute(text: str) -> str:
        """Echo text back, refusing "bad".

        Args:
            text: Text to echo.
        """
        if text == "bad":
            raise ToolError("refused bad")
        return text

    return execute


def echo_twice(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    done = sum(isinstance(m, ChatMessageTool) for m in messages)
    if done == 0:
        return ModelOutput.for_tool_call(MOCK_MODEL, "echo", {"text": "hi"})
    if done == 1:
        return ModelOutput.for_tool_call(MOCK_MODEL, "echo", {"text": "bad"})
    return ModelOutput.from_content(MOCK_MODEL, "finished")


def echo_task(views: list[ScorerView]) -> Task:
    return Task(
        dataset=[Sample(input="go", id="s1")],
        solver=[use_tools(echo()), generate()],
        scorer=record_view(views),
    )


def tools_and_models(events: list[Event]) -> list[ModelEvent | ToolEvent]:
    return [e for e in events if isinstance(e, ModelEvent | ToolEvent)]


def test_scorer_transcript_holds_tool_and_model_events(tmp_path: Path) -> None:
    """In a scorer, transcript().events holds the run's ToolEvents and ModelEvents, in order."""
    views: list[ScorerView] = []
    run_eval(echo_task(views), tmp_path, echo_twice, temperature=0.5)
    [view] = views
    events = tools_and_models(view.events)
    kinds = [type(e).__name__ for e in events]
    assert kinds == ["ModelEvent", "ToolEvent", "ModelEvent", "ToolEvent", "ModelEvent"]
    ok, refused = events[1], events[3]
    assert isinstance(ok, ToolEvent)
    assert isinstance(refused, ToolEvent)
    assert (ok.function, ok.arguments, ok.result, ok.error) == ("echo", {"text": "hi"}, "hi", None)
    assert (refused.function, refused.arguments) == ("echo", {"text": "bad"})
    assert refused.error is not None
    assert refused.error.message == "refused bad"
    last = events[-1]
    assert isinstance(last, ModelEvent)
    assert last.role is None
    assert last.config.temperature == 0.5
    assert (last.output.stop_reason, last.output.completion) == ("stop", "finished")
    first = events[0]
    assert isinstance(first, ModelEvent)
    assert first.output.stop_reason == "tool_calls"


def test_rescore_transcript_holds_the_stored_events(tmp_path: Path) -> None:
    """When score() re-scores a stored log, transcript().events starts with the sample's events."""
    log = read_eval_log(run_eval(echo_task([]), tmp_path, echo_twice).location)
    stored = only_sample(log).events
    views: list[ScorerView] = []
    score(log, record_view(views), action="append", display="none")
    [view] = views
    assert len(view.events) >= len(stored)
    assert [e.uuid for e in view.events[: len(stored)]] == [e.uuid for e in stored]
    events = tools_and_models(view.events)
    assert [type(e).__name__ for e in events] == [
        "ModelEvent",
        "ToolEvent",
        "ModelEvent",
        "ToolEvent",
        "ModelEvent",
    ]
    tool_event = events[1]
    assert isinstance(tool_event, ToolEvent)
    assert (tool_event.function, tool_event.arguments, tool_event.result) == (
        "echo",
        {"text": "hi"},
        "hi",
    )
    final = events[-1]
    assert isinstance(final, ModelEvent)
    assert final.output.stop_reason == "stop"


@scorer(metrics=[mean()])
def judge_config(configs: list[GenerateConfig], roles: list[str | None]) -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        await get_model(role="judge").generate("q", config=CALL_CONFIG)
        event = next(e for e in reversed(transcript().events) if isinstance(e, ModelEvent))
        configs.append(event.config)
        roles.append(event.role)
        return Score(value=1.0)

    return score


def test_role_call_event_records_role_and_merged_config(tmp_path: Path) -> None:
    """A get_model(role=...) call logs a ModelEvent with that role and the merged config used."""
    configs: list[GenerateConfig] = []
    roles: list[str | None] = []
    judge = get_model(MOCK_MODEL, config=ROLE_CONFIG)
    task = Task(
        dataset=[Sample(input="go")], solver=[generate()], scorer=judge_config(configs, roles)
    )
    log = run_eval(task, tmp_path, model_roles={"judge": judge}, max_retries=2)
    assert roles == ["judge"]
    [config] = configs
    # The per-call config wins over the role model's own; unset fields keep the role's;
    # operational settings (max_retries) are inherited from the eval.
    assert config.model_dump(exclude_none=True) == {
        "temperature": 0.0,
        "max_tokens": 1024,
        "top_p": 0.9,
        "max_retries": 2,
    }
    judged = [e for e in only_sample(log).events if isinstance(e, ModelEvent) and e.role == "judge"]
    assert [e.config for e in judged] == [config]
