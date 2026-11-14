# SPDX-License-Identifier: Apache-2.0
"""Contract: stored logs can be re-scored with new scorers without re-running the agent."""

import subprocess
import sys
from pathlib import Path

# score's `scorers` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import (
    Task,
    score,  # pyright: ignore[reportUnknownVariableType]
)
from inspect_ai.dataset import Sample
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalLog, read_eval_log, write_eval_log
from inspect_ai.model import get_model
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, accuracy, mean, scorer
from inspect_ai.solver import TaskState, generate

from .fixtures.support import MOCK_DEFAULT_OUTPUT, run_eval, scripted

CLI_TIMEOUT = 120

CLI_SCORER = """
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState


@scorer(metrics=[mean()])
def completion_length() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return Score(value=float(len(state.output.completion)))

    return score
"""


@scorer(metrics=[mean()])
def original() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return Score(value=1.0)

    return score


@scorer(metrics=[accuracy()])
def llm_judge() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        verdict = (await get_model(role="judge").generate(state.output.completion)).completion
        return Score(value=CORRECT if verdict == "UNSAFE" else INCORRECT, explanation=verdict)

    return score


def stored_log(tmp_path: Path, calls: list[str]) -> EvalLog:
    task = Task(
        dataset=[Sample(input="a", id="a"), Sample(input="b", id="b")],
        solver=[generate()],
        scorer=original(),
    )
    return read_eval_log(run_eval(task, tmp_path, scripted("AGENT", calls)).location)


def model_event_count(log: EvalLog) -> int:
    assert log.samples is not None
    return sum(isinstance(e, ModelEvent) for s in log.samples for e in s.events)


def test_score_appends_new_scorer_without_rerunning_agent(tmp_path: Path) -> None:
    """score(log, scorer) adds a new named score and leaves agent messages untouched."""
    agent_calls: list[str] = []
    log = stored_log(tmp_path, agent_calls)
    judge_calls: list[str] = []
    rescored = score(
        log,
        llm_judge(),
        model_roles={"judge": scripted("UNSAFE", judge_calls)},
        action="append",
        display="none",
    )
    assert agent_calls == ["AGENT", "AGENT"]
    assert judge_calls == ["UNSAFE", "UNSAFE"]
    assert rescored.samples is not None
    for sample in rescored.samples:
        assert sample.output.completion == "AGENT"
        assert sample.scores is not None
        assert set(sample.scores) == {"original", "llm_judge"}
        assert sample.scores["llm_judge"].value == CORRECT
    assert rescored.results is not None
    assert [s.name for s in rescored.results.scores] == ["original", "llm_judge"]
    assert model_event_count(rescored) == model_event_count(log) + 2


def test_score_overwrite_replaces_existing_scores(tmp_path: Path) -> None:
    """action="overwrite" drops the scores that were in the log."""
    log = stored_log(tmp_path, [])
    rescored = score(
        log,
        llm_judge(),
        model_roles={"judge": scripted("SAFE")},
        action="overwrite",
        display="none",
    )
    assert rescored.samples is not None
    assert all(set(s.scores or {}) == {"llm_judge"} for s in rescored.samples)
    assert rescored.results is not None
    assert [s.name for s in rescored.results.scores] == ["llm_judge"]


def test_score_does_not_write_the_log_file(tmp_path: Path) -> None:
    """score() returns a new EvalLog; persisting it needs write_eval_log()."""
    log = stored_log(tmp_path, [])
    before = Path(log.location).read_bytes()
    rescored = score(log, llm_judge(), model_roles={"judge": scripted("UNSAFE")}, display="none")
    assert Path(log.location).read_bytes() == before
    out = tmp_path / "rescored.eval"
    write_eval_log(rescored, str(out))
    reread = read_eval_log(str(out))
    assert reread.samples is not None
    assert all("llm_judge" in (s.scores or {}) for s in reread.samples)


def test_callable_custom_outputs_are_not_reconstructed(tmp_path: Path) -> None:
    """The log stores custom_outputs as None, so re-scoring sees a default-output mock model."""
    log = stored_log(tmp_path, [])
    assert log.eval.model_args == {"custom_outputs": None}
    rescored = score(log, llm_judge(), display="none")
    assert rescored.samples is not None
    explanations = {(s.scores or {})["llm_judge"].explanation for s in rescored.samples}
    assert explanations == {MOCK_DEFAULT_OUTPUT}


def test_inspect_score_cli_rescores_with_scorer_file(tmp_path: Path) -> None:
    """`inspect score LOG --scorer f.py@name --action append --output-file OUT` re-scores."""
    log = stored_log(tmp_path / "logs", [])
    scorer_file = tmp_path / "judge_scorer.py"
    scorer_file.write_text(CLI_SCORER)
    out = tmp_path / "cli.eval"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "inspect_ai",
            "score",
            log.location,
            "--scorer",
            f"{scorer_file.name}@completion_length",
            "--action",
            "append",
            "--display",
            "none",
            "--output-file",
            str(out),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT,
    )
    assert result.returncode == 0, result.stderr
    reread = read_eval_log(str(out))
    assert reread.samples is not None
    for sample in reread.samples:
        assert sample.scores is not None
        assert set(sample.scores) == {"original", "completion_length"}
        assert sample.scores["completion_length"].value == float(len("AGENT"))
