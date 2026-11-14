# SPDX-License-Identifier: Apache-2.0
"""Wilson score interval: reference values, Inspect agreement, properties and validation."""

import itertools
import math
from collections.abc import Callable
from statistics import NormalDist
from typing import cast

import pytest
from inspect_ai.scorer import Metric, MetricProtocol, SampleScore, Score, Value, ci_wilson
from pydantic import ValidationError

from probo.stats import Interval, wilson_interval

Z95 = NormalDist().inv_cdf(0.975)
LEVELS = (0.5, 0.8, 0.9, 0.95, 0.99, 0.999)


def inspect_bounds(successes: int, trials: int, level: float) -> tuple[float, float]:
    """Inspect's ci_wilson metric on x ones and n - x zeros: an independent implementation."""
    scores = [
        SampleScore(score=Score(value=1.0 if i < successes else 0.0), sample_id=i)
        for i in range(trials)
    ]
    metric: Metric = ci_wilson(level=level)
    assert isinstance(metric, MetricProtocol)
    value: Value = metric(scores)
    assert isinstance(value, dict)
    lower, upper = value["lower"], value["upper"]
    assert isinstance(lower, float)
    assert isinstance(upper, float)
    return lower, upper


def test_seven_of_ten_matches_published_reference() -> None:
    """7/10 at 95% is [0.396778, 0.892209] to 6 decimals."""
    interval = wilson_interval(7, 10)
    assert interval.lower == pytest.approx(0.396778, abs=5e-7)
    assert interval.upper == pytest.approx(0.892209, abs=5e-7)


def test_zero_successes_has_exact_zero_lower_and_closed_form_upper() -> None:
    """x = 0: lower is exactly 0.0, upper = z^2 / (n + z^2) = 0.071348 for n = 50 at 95%."""
    interval = wilson_interval(0, 50)
    assert interval.lower == 0.0
    assert interval.upper == pytest.approx(Z95**2 / (50 + Z95**2), rel=1e-12)
    assert interval.upper == pytest.approx(0.071348, abs=5e-7)


def test_all_successes_has_exact_one_upper_and_closed_form_lower() -> None:
    """x = n: upper is exactly 1.0, lower = n / (n + z^2)."""
    for trials in (1, 2, 10, 50, 1000):
        interval = wilson_interval(trials, trials)
        assert interval.upper == 1.0
        assert interval.lower == pytest.approx(trials / (trials + Z95**2), rel=1e-12)


@pytest.mark.parametrize(("trials", "half_width"), [(100, 0.096168), (400, 0.048765)])
def test_half_width_at_one_half(trials: int, half_width: float) -> None:
    """At p = 0.5 the half-width is about 0.096 at n = 100 and 0.049 at n = 400."""
    interval = wilson_interval(trials // 2, trials)
    assert (interval.upper - interval.lower) / 2 == pytest.approx(half_width, abs=5e-7)
    assert (interval.lower + interval.upper) / 2 == pytest.approx(0.5, abs=1e-12)


@pytest.mark.parametrize("level", [0.8, 0.95, 0.99])
@pytest.mark.parametrize("trials", [1, 2, 3, 5, 10, 17, 50, 100])
def test_agrees_with_inspect_ci_wilson(trials: int, level: float) -> None:
    """Every x in [0, n] agrees with Inspect's ci_wilson to 1e-12."""
    for successes in range(trials + 1):
        interval = wilson_interval(successes, trials, level)
        lower, upper = inspect_bounds(successes, trials, level)
        assert interval.lower == pytest.approx(lower, abs=1e-12)
        assert interval.upper == pytest.approx(upper, abs=1e-12)


@pytest.mark.parametrize("level", LEVELS)
def test_bounds_in_unit_interval_and_contain_point_estimate(level: float) -> None:
    """0 <= lower <= x/n <= upper <= 1 for every x, n <= 60."""
    for trials in range(1, 61):
        for successes in range(trials + 1):
            interval = wilson_interval(successes, trials, level)
            assert 0.0 <= interval.lower <= successes / trials <= interval.upper <= 1.0


def test_interval_narrows_as_trials_grow() -> None:
    """At a fixed proportion, more trials give a strictly narrower interval."""
    for p_num, p_den in ((0, 1), (1, 10), (3, 10), (1, 2), (1, 1)):
        widths: list[float] = []
        for scale in (1, 2, 4, 8, 16, 64):
            trials = p_den * 10 * scale
            interval = wilson_interval(p_num * 10 * scale, trials)
            widths.append(interval.upper - interval.lower)
        assert all(a > b for a, b in itertools.pairwise(widths))


def test_symmetric_under_swapping_successes_and_failures() -> None:
    """[L, U] for x successes equals [1 - U, 1 - L] for n - x successes."""
    for trials in range(1, 41):
        for successes in range(trials + 1):
            interval = wilson_interval(successes, trials)
            mirrored = wilson_interval(trials - successes, trials)
            assert interval.lower == pytest.approx(1.0 - mirrored.upper, abs=1e-12)
            assert interval.upper == pytest.approx(1.0 - mirrored.lower, abs=1e-12)


def test_higher_level_gives_wider_interval() -> None:
    """The interval at a higher level contains the interval at a lower one, strictly wider."""
    for successes, trials in ((0, 5), (3, 10), (7, 10), (20, 20), (37, 120)):
        intervals = [wilson_interval(successes, trials, level) for level in LEVELS]
        for narrow, wide in itertools.pairwise(intervals):
            assert wide.lower <= narrow.lower
            assert wide.upper >= narrow.upper
            assert wide.upper - wide.lower > narrow.upper - narrow.lower


def test_matches_textbook_formula() -> None:
    """Agrees with p-hat form (p + z^2/2n +- z sqrt(p(1-p)/n + z^2/4n^2)) / (1 + z^2/n)."""
    for successes, trials in ((1, 3), (7, 10), (13, 29), (250, 1000)):
        p = successes / trials
        z2 = Z95**2
        denominator = 1 + z2 / trials
        center = (p + z2 / (2 * trials)) / denominator
        half = Z95 * math.sqrt(p * (1 - p) / trials + z2 / (4 * trials**2)) / denominator
        interval = wilson_interval(successes, trials)
        assert interval.lower == pytest.approx(center - half, abs=1e-12)
        assert interval.upper == pytest.approx(center + half, abs=1e-12)


def test_interval_is_immutable() -> None:
    """An Interval cannot be modified after construction."""
    interval = wilson_interval(7, 10)
    with pytest.raises(ValidationError):
        interval.__setattr__("lower", 0.0)


@pytest.mark.parametrize(("successes", "trials"), [(0, 0), (0, -1), (-1, 10), (11, 10), (5, 0)])
def test_rejects_counts_out_of_range(successes: int, trials: int) -> None:
    """trials <= 0 and successes outside [0, trials] raise ValueError."""
    with pytest.raises(ValueError):
        wilson_interval(successes, trials)


@pytest.mark.parametrize("level", [0.0, 1.0, -0.5, 1.5, math.nan, math.inf])
def test_rejects_level_outside_open_unit_interval(level: float) -> None:
    """level must be in (0, 1); NaN and infinities are rejected."""
    with pytest.raises(ValueError, match="level"):
        wilson_interval(3, 10, level)


def test_rejects_non_int_counts() -> None:
    """Floats and bools are not counts."""
    untyped = cast(Callable[[object, object], Interval], wilson_interval)
    for successes, trials in [(3.0, 10), (3, 10.0), (True, 10), (1, True)]:
        with pytest.raises(TypeError):
            untyped(successes, trials)


@pytest.mark.parametrize(("lower", "upper"), [(-0.1, 0.5), (0.6, 0.5), (0.2, 1.1)])
def test_interval_rejects_bounds_out_of_order_or_range(lower: float, upper: float) -> None:
    """An Interval needs 0 <= lower <= upper <= 1."""
    with pytest.raises(ValidationError):
        Interval(lower=lower, upper=upper)
