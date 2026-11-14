# SPDX-License-Identifier: Apache-2.0
"""Contract: what eval logs record about samples, events, usage, errors and limits."""

from pathlib import Path

from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.event import ErrorEvent, ModelEvent, SampleLimitEvent, ToolEvent
from inspect_ai.log import EvalLog, EvalSample, read_eval_log
from inspect_ai.model import ChatMessage, ChatMessageTool, GenerateConfig, ModelOutput
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, generate, solver, use_tools
from inspect_ai.tool import Tool, ToolChoice, ToolError, ToolInfo, tool
from inspect_ai.util import store

from .fixtures.support import MOCK_MODEL, OutputFn, only_sample, run_eval


@tool
def ping() -> Tool:
    async def execute() -> str:
        """Ping."""
        return "pong"

    return execute


@tool
def crash() -> Tool:
    async def execute() -> str:
        """Raise a plain exception."""
        raise RuntimeError("tool exploded")

    return execute


@tool
def refuse() -> Tool:
    async def execute() -> str:
        """Raise a ToolError."""
        raise ToolError("not allowed")

    return execute


@solver
def explode_on(sample_id: str) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        if state.sample_id == sample_id:
            raise RuntimeError("solver exploded")
        return state

    return solve


@scorer(metrics=[mean()])
def message_count() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return Score(value=float(len(state.messages)))

    return score


def call_once(tool_name: str) -> OutputFn:
    def script(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if isinstance(messages[-1], ChatMessageTool):
            return ModelOutput.from_content(MOCK_MODEL, "finished")
        return ModelOutput.for_tool_call(MOCK_MODEL, tool_name, {})

    return script


def call_forever(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    return ModelOutput.for_tool_call(MOCK_MODEL, "ping", {})


def run_tool(
    tmp_path: Path, agent_tool: Tool, tool_name: str, fail_on_error: bool | None = None
) -> EvalLog:
    task = Task(
        dataset=[Sample(input="go", id="s1", metadata={"suite": "smoke"})],
        solver=[use_tools(agent_tool), generate()],
        scorer=message_count(),
    )
    return run_eval(task, tmp_path, call_once(tool_name), fail_on_error=fail_on_error)


def test_read_eval_log_round_trips_written_file(tmp_path: Path) -> None:
    """eval() writes a .eval file under log_dir that read_eval_log() loads with samples."""
    log = run_tool(tmp_path, ping(), "ping")
    assert log.location.endswith(".eval")
    assert Path(log.location).parent == tmp_path
    sample = only_sample(read_eval_log(log.location))
    assert (sample.id, sample.epoch, sample.metadata) == ("s1", 1, {"suite": "smoke"})
    assert sample.scores is not None
    assert sample.scores["message_count"].value == 4.0


def test_events_include_model_and_tool_events(tmp_path: Path) -> None:
    """Sample events hold ModelEvent and ToolEvent records in execution order."""
    sample = only_sample(read_eval_log(run_tool(tmp_path, ping(), "ping").location))
    events = [e for e in sample.events if isinstance(e, ModelEvent | ToolEvent)]
    assert [type(e).__name__ for e in events] == ["ModelEvent", "ToolEvent", "ModelEvent"]
    tool_event = events[1]
    assert isinstance(tool_event, ToolEvent)
    assert (tool_event.function, tool_event.arguments, tool_event.result) == ("ping", {}, "pong")
    assert tool_event.error is None
    first_model = events[0]
    assert isinstance(first_model, ModelEvent)
    assert first_model.model == MOCK_MODEL
    assert first_model.output.message.tool_calls is not None


def test_model_usage_recorded_per_sample_and_eval(tmp_path: Path) -> None:
    """Token usage is keyed by model name on each sample and in log.stats."""
    log = run_tool(tmp_path, ping(), "ping")
    sample_usage = only_sample(log).model_usage[MOCK_MODEL]
    assert sample_usage.total_tokens > 0
    assert sample_usage.total_tokens == sample_usage.input_tokens + sample_usage.output_tokens
    assert log.stats.model_usage[MOCK_MODEL].total_tokens == sample_usage.total_tokens


def test_solver_exception_recorded_on_sample(tmp_path: Path) -> None:
    """With fail_on_error=False a raising solver sets sample.error, skips scoring, eval succeeds."""
    task = Task(
        dataset=[Sample(input="a", id="good"), Sample(input="b", id="bad")],
        solver=[explode_on("bad"), generate()],
        scorer=message_count(),
    )
    log = run_eval(task, tmp_path, fail_on_error=False)
    assert log.status == "success"
    assert log.samples is not None
    by_id = {s.id: s for s in read_eval_log(log.location).samples or []}
    bad = by_id["bad"]
    assert bad.error is not None
    assert bad.error.message == "RuntimeError('solver exploded')"
    assert "solver exploded" in bad.error.traceback
    assert bad.scores == {}
    assert any(isinstance(e, ErrorEvent) for e in bad.events)
    assert by_id["good"].error is None
    assert by_id["good"].scores is not None


def test_default_fail_on_error_fails_the_eval(tmp_path: Path) -> None:
    """Without fail_on_error, one sample error sets log.status to "error"."""
    log = run_eval(
        Task(dataset=[Sample(input="b", id="bad")], solver=[explode_on("bad")]), tmp_path
    )
    assert log.status == "error"
    assert log.error is not None
    assert log.error.message == "RuntimeError('solver exploded')"


def test_plain_tool_exception_is_a_sample_error(tmp_path: Path) -> None:
    """A tool raising a non-ToolError exception errors the whole sample, not just the call."""
    sample = only_sample(run_tool(tmp_path, crash(), "crash", fail_on_error=False))
    assert sample.error is not None
    assert sample.error.message == "RuntimeError('tool exploded')"
    assert sample.scores == {}
    assert not any(isinstance(m, ChatMessageTool) for m in sample.messages)


def test_tool_error_becomes_tool_result(tmp_path: Path) -> None:
    """ToolError is returned to the model as a tool message with .error and the sample goes on."""
    sample = only_sample(run_tool(tmp_path, refuse(), "refuse"))
    assert sample.error is None
    [tool_message] = [m for m in sample.messages if isinstance(m, ChatMessageTool)]
    assert tool_message.error is not None
    assert tool_message.error.message == "not allowed"
    [tool_event] = [e for e in sample.events if isinstance(e, ToolEvent)]
    assert tool_event.error is not None
    assert tool_event.error.message == "not allowed"
    assert sample.output.completion == "finished"


def run_until_limit(
    tmp_path: Path, message_limit: int | None = None, token_limit: int | None = None
) -> EvalSample:
    task = Task(
        dataset=[Sample(input="go")],
        solver=[use_tools(ping()), generate()],
        scorer=message_count(),
    )
    log = run_eval(
        task, tmp_path, call_forever, message_limit=message_limit, token_limit=token_limit
    )
    return only_sample(log)


def test_message_limit_recorded_as_sample_limit(tmp_path: Path) -> None:
    """Hitting message_limit sets sample.limit (not error) and scorers still run."""
    sample = run_until_limit(tmp_path, message_limit=5)
    assert sample.error is None
    assert sample.limit is not None
    assert (sample.limit.type, sample.limit.limit) == ("message", 5)
    assert len(sample.messages) == 5
    assert sample.scores is not None
    assert sample.scores["message_count"].value == 5.0
    assert any(isinstance(e, SampleLimitEvent) and e.type == "message" for e in sample.events)


def test_token_limit_recorded_and_can_overshoot(tmp_path: Path) -> None:
    """Hitting token_limit sets sample.limit type "token"; usage may exceed the limit."""
    sample = run_until_limit(tmp_path, token_limit=300)
    assert sample.error is None
    assert sample.limit is not None
    assert (sample.limit.type, sample.limit.limit) == ("token", 300)
    assert sample.model_usage[MOCK_MODEL].total_tokens > 300
    assert sample.scores is not None


def test_store_is_logged_per_sample(tmp_path: Path) -> None:
    """Values put in the sample store during the run are serialised to EvalSample.store."""

    @solver
    def remember() -> Solver:
        async def solve(state: TaskState, generate: Generate) -> TaskState:
            store().set("seen", state.sample_id)
            return state

        return solve

    log = run_eval(Task(dataset=[Sample(input="a", id="a")], solver=[remember()]), tmp_path)
    assert only_sample(read_eval_log(log.location)).store == {"seen": "a"}
