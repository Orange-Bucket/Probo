# SPDX-License-Identifier: Apache-2.0
"""Contract: epochs, epoch reducers, ci_wilson and clustered stderr."""

import math
from pathlib import Path
from statistics import NormalDist

import pytest
from inspect_ai import Epochs, Task
from inspect_ai.dataset import Sample
from inspect_ai.log import EvalLog
from inspect_ai.scorer import (
    Metric,
    MetricProtocol,
    SampleScore,
    Score,
    Scorer,
    Target,
    Value,
    accuracy,
    ci,
    ci_wilson,
    mean,
    scorer,
    stderr,
)
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.util import store

from .fixtures.support import run_eval

SUCCESSES = 7
TRIALS = 10
CLUSTER_SIZE = 5


@solver
def bump_counter() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        store().set("runs", store().get("runs", 0) + 1)
        return state

    return solve


@scorer(metrics=[mean()])
def odd_epoch() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return Score(
            value=float(state.epoch % 2),
            metadata={"epoch": state.epoch, "runs": store().get("runs")},
        )

    return score


@scorer(metrics=[accuracy(), stderr(), stderr(cluster="group"), ci(), ci_wilson()])
def flagged() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        return Score(value="C" if state.metadata["hit"] else "I")

    return score


def binary_samples() -> list[Sample]:
    return [
        Sample(input="x", id=i, metadata={"hit": i < SUCCESSES, "group": i // CLUSTER_SIZE})
        for i in range(TRIALS)
    ]


def binary_sample_scores() -> list[SampleScore]:
    return [
        SampleScore(
            score=Score(value=1.0 if i < SUCCESSES else 0.0),
            sample_id=i,
            sample_metadata={"group": i // CLUSTER_SIZE},
        )
        for i in range(TRIALS)
    ]


def compute(metric: Metric, scores: list[SampleScore]) -> Value:
    assert isinstance(metric, MetricProtocol)
    return metric(scores)


def bounds(value: Value) -> tuple[float, float]:
    assert isinstance(value, dict)
    assert set(value) == {"lower", "upper"}
    lower, upper = value["lower"], value["upper"]
    assert isinstance(lower, float)
    assert isinstance(upper, float)
    return lower, upper


def hand_wilson(successes: int, trials: int, level: float = 0.95) -> tuple[float, float]:
    z = NormalDist().inv_cdf(1 - (1 - level) / 2)
    p = successes / trials
    denominator = 1 + z * z / trials
    center = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return center - half, center + half


def run_epochs(tmp_path: Path, epochs: int | Epochs) -> EvalLog:
    task = Task(
        dataset=[Sample(input="a", id="a"), Sample(input="b", id="b")],
        solver=[bump_counter()],
        scorer=odd_epoch(),
        epochs=epochs,
    )
    return run_eval(task, tmp_path)


def test_epochs_log_one_sample_per_epoch_with_fresh_store(tmp_path: Path) -> None:
    """Each (sample, epoch) is its own EvalSample with unreduced scores and a fresh store."""
    log = run_epochs(tmp_path, 3)
    assert log.samples is not None
    assert sorted((s.id, s.epoch) for s in log.samples) == [
        (sid, e) for sid in ("a", "b") for e in (1, 2, 3)
    ]
    for sample in log.samples:
        assert sample.store["runs"] == 1
        assert sample.scores is not None
        assert sample.scores["odd_epoch"].value == float(sample.epoch % 2)


def test_int_epochs_default_to_unnamed_mean_reducer(tmp_path: Path) -> None:
    """epochs=N reduces with mean, but config, EvalScore and reductions record reducer None."""
    log = run_epochs(tmp_path, 3)
    assert log.eval.config.epochs == 3
    assert log.eval.config.epochs_reducer is None
    assert log.results is not None
    [eval_score] = log.results.scores
    assert eval_score.reducer is None
    assert eval_score.metrics["mean"].value == pytest.approx(2 / 3)
    assert log.reductions is not None
    assert [r.reducer for r in log.reductions] == [None]


def test_explicit_single_reducer_is_recorded_by_name(tmp_path: Path) -> None:
    """Epochs(n, "max") records reducer "max" in config and on the EvalScore."""
    log = run_epochs(tmp_path, Epochs(3, "max"))
    assert log.eval.config.epochs_reducer == ["max"]
    assert log.results is not None
    [eval_score] = log.results.scores
    assert eval_score.reducer == "max"
    assert eval_score.metrics["mean"].value == 1.0


def test_multiple_reducers_yield_same_named_eval_scores(tmp_path: Path) -> None:
    """Epochs(n, [reducers]) yields one EvalScore per reducer, all sharing the scorer name."""
    log = run_epochs(tmp_path, Epochs(3, ["mean", "max", "at_least_2"]))
    assert log.results is not None
    by_reducer = {s.reducer: s for s in log.results.scores}
    assert [s.name for s in log.results.scores] == ["odd_epoch"] * 3
    assert by_reducer["mean"].metrics["mean"].value == pytest.approx(2 / 3)
    assert by_reducer["max"].metrics["mean"].value == 1.0
    assert by_reducer["at_least_2"].metrics["mean"].value == 1.0


def test_log_reductions_hold_reduced_per_sample_scores(tmp_path: Path) -> None:
    """EvalLog.reductions keeps one reduced score per sample id for each reducer."""
    log = run_epochs(tmp_path, Epochs(3, ["mean", "max"]))
    assert log.reductions is not None
    reductions = {(r.scorer, r.reducer): r for r in log.reductions}
    assert set(reductions) == {("odd_epoch", "mean"), ("odd_epoch", "max")}
    mean_values = {s.sample_id: s.value for s in reductions[("odd_epoch", "mean")].samples}
    assert mean_values == {"a": pytest.approx(2 / 3), "b": pytest.approx(2 / 3)}


def test_ci_wilson_returns_lower_upper_mapping() -> None:
    """ci_wilson() returns {"lower", "upper"} bounds equal to the textbook Wilson interval."""
    expected_lower, expected_upper = hand_wilson(SUCCESSES, TRIALS)
    lower, upper = bounds(compute(ci_wilson(), binary_sample_scores()))
    assert lower == pytest.approx(expected_lower, abs=1e-12)
    assert upper == pytest.approx(expected_upper, abs=1e-12)
    assert lower == pytest.approx(0.396778, abs=1e-6)
    assert upper == pytest.approx(0.892209, abs=1e-6)


def test_ci_wilson_level_changes_width() -> None:
    """ci_wilson(level=...) sets the confidence level of the interval."""
    expected_lower, expected_upper = hand_wilson(SUCCESSES, TRIALS, level=0.8)
    lower, upper = bounds(compute(ci_wilson(level=0.8), binary_sample_scores()))
    assert lower == pytest.approx(expected_lower, abs=1e-12)
    assert upper == pytest.approx(expected_upper, abs=1e-12)


def test_ci_wilson_cluster_widens_interval() -> None:
    """ci_wilson(cluster=...) uses a Korn-Graubard effective n and a t critical value."""
    plain_lower, plain_upper = bounds(compute(ci_wilson(), binary_sample_scores()))
    lower, upper = bounds(compute(ci_wilson(cluster="group"), binary_sample_scores()))
    assert lower == pytest.approx(0.006990, abs=1e-6)
    assert upper == pytest.approx(0.998709, abs=1e-6)
    assert lower < plain_lower
    assert upper > plain_upper


def test_stderr_cluster_uses_sample_metadata() -> None:
    """stderr(cluster=key) clusters on a sample metadata key and changes the value."""
    p = SUCCESSES / TRIALS
    plain = compute(stderr(), binary_sample_scores())
    clustered = compute(stderr(cluster="group"), binary_sample_scores())
    assert plain == pytest.approx(math.sqrt(p * (1 - p) * TRIALS / (TRIALS - 1) / TRIALS))
    assert clustered == pytest.approx(0.3)


def test_stderr_cluster_missing_key_raises() -> None:
    """stderr(cluster=key) raises when a sample lacks that metadata key."""
    with pytest.raises(ValueError, match="no cluster metadata"):
        compute(stderr(cluster="absent"), binary_sample_scores())


def test_dict_metrics_are_flattened_with_numbered_keys(tmp_path: Path) -> None:
    """In EvalScore.metrics, dict-valued metrics flatten to "lower"/"upper", then "lower2"..."""
    log = run_eval(Task(dataset=binary_samples(), solver=[], scorer=flagged()), tmp_path)
    assert log.results is not None
    [eval_score] = log.results.scores
    metrics = eval_score.metrics
    assert list(metrics) == ["accuracy", "stderr", "stderr2", "lower", "upper", "lower2", "upper2"]
    assert metrics["stderr2"].name == "stderr"
    assert metrics["stderr2"].params == {"cluster": "group"}
    assert metrics["stderr2"].value == pytest.approx(0.3)
    assert metrics["upper"].value > 1.0
    wilson_lower, wilson_upper = hand_wilson(SUCCESSES, TRIALS)
    assert metrics["lower2"].value == pytest.approx(wilson_lower)
    assert metrics["upper2"].value == pytest.approx(wilson_upper)
