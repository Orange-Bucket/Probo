# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for the contract tests: scripted mockllm runs, a recording scorer and Docker
bookkeeping."""

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

# eval's `scanner` and task_with's `scorer` parameters are typed via the optional
# inspect_scout package (not installed).
from inspect_ai import Task, task_with  # pyright: ignore[reportUnknownVariableType]
from inspect_ai import eval as inspect_eval  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.event import Event
from inspect_ai.log import EvalLog, EvalSample, transcript
from inspect_ai.model import ChatMessage, GenerateConfig, Model, ModelOutput, get_model
from inspect_ai.scorer import Score, Scorer, Target, scorer
from inspect_ai.solver import TaskState
from inspect_ai.tool import ToolChoice, ToolInfo

FIXTURES = Path(__file__).resolve().parent
MOCK_MODEL = "mockllm/model"
MOCK_DEFAULT_OUTPUT = "Default output from mockllm/model"
# Must match every `image:` and `FROM` under fixtures/; conftest checks this one is usable.
IMAGE = "python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b"
# Default per-sample cap, so a scripted loop whose exit condition stops matching fails
# on the limit instead of hanging.
MESSAGE_LIMIT = 20

OutputFn = Callable[[list[ChatMessage], list[ToolInfo], ToolChoice, GenerateConfig], ModelOutput]
Outputs = Sequence[ModelOutput] | OutputFn


def mock_model(outputs: Outputs = ()) -> Model:
    """A mockllm model replaying `outputs`, or giving its default text when there are none."""
    return get_model(MOCK_MODEL, custom_outputs=outputs or None)


def scripted(text: str, calls: list[str] | None = None) -> Model:
    """A mockllm model that always replies `text`, appending it to `calls` on each generate."""

    def reply(
        messages: list[ChatMessage],
        tools: list[ToolInfo],
        tool_choice: ToolChoice,
        config: GenerateConfig,
    ) -> ModelOutput:
        if calls is not None:
            calls.append(text)
        return ModelOutput.from_content(MOCK_MODEL, text)

    return mock_model(reply)


@dataclass(frozen=True)
class ScorerView:
    """What a scorer saw when it ran."""

    events: list[Event]
    """`transcript().events` at the time the scorer ran."""
    output: ModelOutput
    """`state.output`."""
    messages: list[ChatMessage]
    """`state.messages`."""


@scorer(metrics=[])
def record_view(views: list[ScorerView]) -> Scorer:
    """A scorer that appends what it sees (transcript events, output, messages) to `views`."""

    async def score(state: TaskState, target: Target) -> Score:
        views.append(ScorerView(list(transcript().events), state.output, list(state.messages)))
        return Score(value=1.0)

    return score


def run_eval(
    task: Task,
    log_dir: Path,
    model: Model | Outputs = (),
    **eval_args: Any,
) -> EvalLog:
    """Run one task quietly into log_dir and return its log.

    `model` is a Model or the outputs for mock_model(). message_limit defaults to
    MESSAGE_LIMIT; pass message_limit=None to lift it.
    """
    if not isinstance(model, Model):
        model = mock_model(model)
    eval_args.setdefault("message_limit", MESSAGE_LIMIT)
    logs = inspect_eval(task, model=model, log_dir=str(log_dir), display="none", **eval_args)
    assert len(logs) == 1
    return logs[0]


def inspect_compose_projects(prefix: str) -> set[str]:
    """Compose projects named with `prefix` that still own a container or network."""
    label = "com.docker.compose.project"
    template = f'{{{{.Label "{label}"}}}}'
    projects: set[str] = set()
    for kind in (["ps", "-a"], ["network", "ls"]):
        result = subprocess.run(
            ["docker", *kind, "--filter", f"label={label}", "--format", template],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        projects.update(line for line in result.stdout.split() if line.startswith(prefix))
    return projects


def run_docker_eval(
    task: Task,
    log_dir: Path,
    model: Model | Outputs = (),
    **eval_args: Any,
) -> EvalLog:
    """Like run_eval, and also assert the run left no Compose project behind.

    The task gets a unique name, which Inspect embeds in its project names
    (inspect-<name[:12]>-i<id>), so other Docker activity on the host cannot
    affect the check.
    """
    name = f"probo-{uuid4().hex[:6]}"
    log = run_eval(task_with(task, name=name), log_dir, model, **eval_args)
    leftovers = inspect_compose_projects(f"inspect-{name}-i")
    assert not leftovers, f"Compose projects left behind: {leftovers}"
    return log


def samples(log: EvalLog) -> list[EvalSample]:
    """Samples of a successful log, failing loudly with the eval error otherwise."""
    assert log.status == "success", log.error
    assert log.samples is not None
    return log.samples


def only_sample(log: EvalLog) -> EvalSample:
    """The single sample of a successful log."""
    (sample,) = samples(log)
    return sample
