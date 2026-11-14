# SPDX-License-Identifier: Apache-2.0
"""Contract: how model, retry, scorer and cancellation failures are recorded in a sample.

`probo.outcomes.label` tells a provider error from a grader or harness error by comparing
`EvalSample.error` with the errored ModelEvents, matching the `RetryError(...)` text, and
looking for the `scorers` span before the first ErrorEvent; it treats the cancellation
markers below as "cancelled, not failed". `probo.judges.reply_only` imports
`TerminateSampleError` from its private path to let it propagate.
"""

import re
from collections.abc import Sequence
from pathlib import Path

import anyio
import pytest
from inspect_ai import Task

# Not exported publicly; Probo imports it from here (pinned inspect-ai version).
from inspect_ai._util.exception import TerminateSampleError
from inspect_ai.dataset import Sample
from inspect_ai.event import ErrorEvent, Event, ModelEvent, SampleLimitEvent, SpanBeginEvent

# Not exported publicly: the cancellation sentinels stamped on ModelEvent.error.
from inspect_ai.event._model import (
    CANCEL_ERRORS,
    LIMIT_CANCEL_ERROR,
    OPERATOR_CANCEL_ERROR,
    SYSTEM_CANCEL_ERROR,
)
from inspect_ai.log import EvalSample, read_eval_log
from inspect_ai.model import ChatMessage, GenerateConfig, ModelOutput, get_model
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import Generate, Solver, TaskState, generate, solver
from inspect_ai.tool import ToolChoice, ToolInfo

from .fixtures.support import MOCK_MODEL, OutputFn, only_sample, run_eval

RETRY_ERROR = re.compile(r"RetryError\(<Future at 0x[0-9a-f]+ state=finished raised (\w+)>\)")


class ProviderError(Exception):
    """An exception carrying a `message` attribute, as many provider SDK errors do."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def raising(error: Exception) -> OutputFn:
    def script(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        raise error

    return script


def model_events(events: Sequence[Event]) -> list[tuple[int, ModelEvent]]:
    return [(i, e) for i, e in enumerate(events) if isinstance(e, ModelEvent)]


def first_error_event(events: Sequence[Event]) -> tuple[int, ErrorEvent]:
    return next((i, e) for i, e in enumerate(events) if isinstance(e, ErrorEvent))


def run_generate(tmp_path: Path, script: object, **eval_args: object) -> EvalSample:
    task = Task(dataset=[Sample(input="go")], solver=[generate()])
    model = get_model(MOCK_MODEL, custom_outputs=script)
    log = run_eval(task, tmp_path, model, fail_on_error=False, **eval_args)
    return only_sample(read_eval_log(log.location))


def test_terminate_sample_error_private_path() -> None:
    """TerminateSampleError is importable from inspect_ai._util.exception and is an Exception."""
    assert TerminateSampleError.__module__ == "inspect_ai._util.exception"
    assert issubclass(TerminateSampleError, RuntimeError)
    error = TerminateSampleError("stop")
    assert (error.reason, str(error)) == ("stop", "stop")


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (RuntimeError("provider down"), "RuntimeError('provider down')"),
        (ProviderError("rate limited"), "rate limited"),
    ],
)
def test_generate_error_matches_model_event_error(
    tmp_path: Path, error: Exception, expected: str
) -> None:
    """A raising generate sets sample.error.message == ModelEvent.error and logs an ErrorEvent."""
    sample = run_generate(tmp_path, raising(error))
    assert sample.error is not None
    assert sample.error.message == expected
    [(model_index, event)] = model_events(sample.events)
    assert event.error == expected
    assert event.traceback is not None
    error_index, error_event = first_error_event(sample.events)
    assert error_event.error.message == expected
    assert model_index < error_index


def test_exhausted_retries_give_retry_error_naming_the_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With retries exhausted the sample error is RetryError(...raised NAME); events keep NAME."""
    model = get_model(MOCK_MODEL, custom_outputs=raising(RuntimeError("provider down")))

    def always_retry(ex: Exception) -> bool:
        return True

    def no_wait() -> object:
        # Inspect's default backoff waits ~3-6 s before the retry; the error text does
        # not depend on the wait.
        def wait(retry_state: object) -> float:
            return 0.0

        return wait

    monkeypatch.setattr(model.api, "should_retry", always_retry)
    monkeypatch.setattr(model.api, "retry_wait", no_wait)
    task = Task(dataset=[Sample(input="go")], solver=[generate()])
    log = run_eval(task, tmp_path, model, fail_on_error=False, max_retries=1)
    sample = only_sample(read_eval_log(log.location))
    assert sample.error is not None
    match = RETRY_ERROR.fullmatch(sample.error.message)
    assert match is not None, sample.error.message
    assert match[1] == "RuntimeError"
    events = model_events(sample.events)
    assert [e.error for _, e in events] == ["RuntimeError('provider down')"] * 2
    for _, event in events:
        assert event.traceback is not None
        assert event.traceback.rstrip().splitlines()[-1] == "RuntimeError: provider down"
    _, error_event = first_error_event(sample.events)
    assert error_event.error.message == sample.error.message


@scorer(metrics=[mean()])
def exploding_scorer() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        raise RuntimeError("scorer exploded")

    return score


@solver
def exploding_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        raise RuntimeError("solver exploded")

    return solve


def spans_before(events: Sequence[Event], end: int) -> list[tuple[str, str]]:
    return [(e.type or "", e.name) for e in events[:end] if isinstance(e, SpanBeginEvent)]


def test_scorer_error_follows_scorers_span(tmp_path: Path) -> None:
    """A scorer error's ErrorEvent comes after SpanBegin type "scorers" and type "scorer"."""
    task = Task(dataset=[Sample(input="go")], solver=[generate()], scorer=exploding_scorer())
    log = run_eval(task, tmp_path, fail_on_error=False)
    sample = only_sample(read_eval_log(log.location))
    assert sample.error is not None
    assert sample.error.message == "RuntimeError('scorer exploded')"
    index, _ = first_error_event(sample.events)
    spans = spans_before(sample.events, index)
    assert ("scorers", "scorers") in spans
    assert spans.index(("scorers", "scorers")) < spans.index(("scorer", "exploding_scorer"))


def test_solver_error_has_no_scorers_span_before_it(tmp_path: Path) -> None:
    """A solver error's ErrorEvent comes before any SpanBegin of type "scorers"."""
    task = Task(
        dataset=[Sample(input="go")], solver=[exploding_solver()], scorer=exploding_scorer()
    )
    log = run_eval(task, tmp_path, fail_on_error=False)
    sample = only_sample(read_eval_log(log.location))
    assert sample.error is not None
    assert sample.error.message == "RuntimeError('solver exploded')"
    index, _ = first_error_event(sample.events)
    assert all(span_type != "scorers" for span_type, _ in spans_before(sample.events, index))


def test_cancel_sentinels() -> None:
    """Inspect's ModelEvent cancel sentinels (stamped by its ACP transport) keep their text."""
    assert OPERATOR_CANCEL_ERROR == "Cancelled by operator"
    assert LIMIT_CANCEL_ERROR == "Cancelled by limit"
    assert SYSTEM_CANCEL_ERROR == "Cancelled by system"
    assert {"Cancelled by operator", "Cancelled by limit", "Cancelled by system"} == CANCEL_ERRORS


async def hang(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    await anyio.sleep(30)
    return ModelOutput.from_content(MOCK_MODEL, "too late")


def test_time_limit_marks_in_flight_call_cancelled(tmp_path: Path) -> None:
    """A time limit cutting off a pending call: its ModelEvent errs "model call cancelled"."""
    sample = run_generate(tmp_path, hang, time_limit=1)
    assert sample.error is None
    assert sample.limit is not None
    assert sample.limit.type == "time"
    assert any(isinstance(e, SampleLimitEvent) and e.type == "time" for e in sample.events)
    [(_, event)] = model_events(sample.events)
    assert event.error == "RuntimeError('model call cancelled')"
    assert event.pending is None
