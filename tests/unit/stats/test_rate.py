# SPDX-License-Identifier: Apache-2.0
"""Proportion and Rate: derived values, loading, copying, rendering and validation."""

import json
import re
from decimal import Decimal

import pytest
from pydantic import ValidationError

from probo.stats import Estimand, Interval, Proportion, Rate, wilson_interval
from probo.stats.rate import format_estimate_and_interval, format_level

NUMBERS = re.compile(r"^(\S+) \[(\S+), (\S+)\] \(")


def per_attempt(successes: int, trials: int, level: float = 0.95) -> Rate:
    return Rate.from_counts(successes, trials, estimand=Estimand.PER_ATTEMPT, level=level)


def printed(text: str) -> tuple[Decimal, Decimal, Decimal]:
    match = NUMBERS.match(text)
    assert match is not None
    estimate, lower, upper = match.groups()
    return Decimal(estimate), Decimal(lower), Decimal(upper)


def test_rate_stores_counts_and_computes_estimate_and_interval() -> None:
    """estimate = x / n and interval = Wilson(x, n, level) are computed, not stored."""
    rate = per_attempt(6, 20, level=0.9)
    assert (rate.successes, rate.trials, rate.level) == (6, 20, 0.9)
    assert rate.estimate == 0.3
    assert rate.interval == wilson_interval(6, 20, 0.9)
    assert rate.estimand is Estimand.PER_ATTEMPT
    assert set(Rate.model_fields) == {"successes", "trials", "level", "estimand"}


def test_estimand_values() -> None:
    """Exactly the two computed estimands exist."""
    assert [e.value for e in Estimand] == ["per_attempt", "per_trial"]


def test_dump_includes_derived_values_and_loads_back_equal() -> None:
    """JSON and Python dumps carry estimate and interval and re-validate to an equal rate."""
    for rate in (per_attempt(6, 20), per_attempt(0, 50, 0.99), per_attempt(13, 13)):
        dumped = json.loads(rate.model_dump_json())
        assert dumped["estimate"] == rate.estimate
        assert dumped["interval"] == {"lower": rate.interval.lower, "upper": rate.interval.upper}
        assert Rate.model_validate_json(rate.model_dump_json()) == rate
        assert Rate.model_validate(rate.model_dump()) == rate


def test_derived_keys_are_optional_on_load() -> None:
    """Input without estimate and interval is complete; they are recomputed."""
    loaded = Rate.model_validate(
        {"successes": 6, "trials": 20, "level": 0.95, "estimand": "per_attempt"}
    )
    assert loaded == per_attempt(6, 20)


def test_derived_values_within_tolerance_are_accepted_and_recomputed() -> None:
    """A last-digit difference (another platform's libm) loads; the model holds its own value."""
    rate = per_attempt(6, 20)
    fields = rate.model_dump()
    nudged = {"lower": rate.interval.lower + 1e-15, "upper": rate.interval.upper - 1e-15}
    loaded = Rate.model_validate({**fields, "interval": nudged})
    assert loaded.interval == rate.interval


def test_tampered_derived_values_in_json_are_refused() -> None:
    """A supplied estimate or interval that disagrees with the counts never silently wins."""
    rate = per_attempt(6, 20)
    text = rate.model_dump_json()
    with pytest.raises(ValidationError, match="estimate"):
        Rate.model_validate_json(text.replace('"estimate":0.3', '"estimate":0.9'))
    tampered = json.loads(text)
    tampered["interval"]["upper"] = 0.4
    with pytest.raises(ValidationError, match=r"interval\.upper"):
        Rate.model_validate_json(json.dumps(tampered))
    tampered["interval"] = {"lower": 0.6, "upper": 0.4}
    with pytest.raises(ValidationError):
        Rate.model_validate_json(json.dumps(tampered))
    with pytest.raises(ValidationError, match="must be a number"):
        Rate.model_validate({**rate.model_dump(), "estimate": "0.3"})
    with pytest.raises(ValidationError, match=r"interval\.lower"):
        Rate.model_validate({**rate.model_dump(), "level": 0.9})


def test_model_copy_revalidates() -> None:
    """model_copy(update=...) cannot set a derived value or break an invariant."""
    rate = per_attempt(6, 20)
    with pytest.raises(ValidationError, match="estimate"):
        rate.model_copy(update={"estimate": 0.9})
    with pytest.raises(ValidationError, match="interval"):
        rate.model_copy(update={"interval": Interval(lower=0.0, upper=1.0)})
    with pytest.raises(ValidationError, match="successes"):
        rate.model_copy(update={"successes": 21})
    with pytest.raises(ValidationError, match="level"):
        rate.model_copy(update={"level": 1.0})
    with pytest.raises(ValidationError):
        rate.model_copy(update={"k": 3})
    copied = rate.model_copy(update={"successes": 7})
    assert copied == per_attempt(7, 20)
    assert copied.render().startswith("0.350 ")
    assert rate.model_copy(deep=True) == rate


def test_interval_model_copy_revalidates() -> None:
    """An Interval copy cannot leave [0, 1] or invert its bounds."""
    interval = wilson_interval(1, 2)
    with pytest.raises(ValidationError):
        interval.model_copy(update={"lower": 0.99})
    with pytest.raises(ValidationError):
        interval.model_copy(update={"upper": 1.5})


def test_rate_cannot_be_built_without_trials_level_or_estimand() -> None:
    """Every stored field is required: a bare estimate is not a Rate."""
    with pytest.raises(ValidationError):
        Rate.model_validate({"estimate": 0.3, "estimand": "per_attempt"})
    with pytest.raises(ValidationError):
        Rate.model_validate({"successes": 6, "trials": 20, "level": 0.95})


def test_rate_is_frozen_and_rejects_unknown_fields() -> None:
    """Rates are immutable and do not accept extra keys."""
    rate = per_attempt(6, 20)
    with pytest.raises(ValidationError):
        rate.__setattr__("successes", 7)
    with pytest.raises(ValidationError):
        Rate.model_validate({**rate.model_dump(), "accuracy": 0.9})
    with pytest.raises(ValidationError):
        Rate.model_validate({**rate.model_dump(), "estimand": "at_least_one_of_k"})


@pytest.mark.parametrize(("successes", "trials"), [(0, 0), (-1, 5), (6, 5)])
def test_rate_rejects_invalid_counts(successes: int, trials: int) -> None:
    """Zero trials and successes outside [0, trials] raise ValueError."""
    with pytest.raises(ValueError):
        per_attempt(successes, trials)


def test_rate_rejects_bool_and_float_counts_on_validation() -> None:
    """Strict validation does not coerce bools or floats into counts."""
    fields = per_attempt(1, 1).model_dump()
    with pytest.raises(ValidationError):
        Rate.model_validate({**fields, "successes": True})
    with pytest.raises(ValidationError):
        Rate.model_validate({**fields, "trials": 1.0})


@pytest.mark.parametrize("level", [0.0, 1.0, 5.0, float("nan")])
def test_rejects_level_outside_open_unit_interval(level: float) -> None:
    """level outside (0, 1) is refused for both Rate and Proportion."""
    with pytest.raises(ValueError, match="level"):
        Proportion.from_counts(1, 2, level=level)
    with pytest.raises(ValueError, match="level"):
        per_attempt(1, 2, level=level)


def test_proportion_has_no_estimand_and_renders_without_label() -> None:
    """A Proportion is a bare x / n with Wilson interval, rendered without an estimand."""
    proportion = Proportion.from_counts(8, 10)
    assert proportion.estimate == 0.8
    assert proportion.interval == wilson_interval(8, 10)
    assert proportion.render() == "0.800 [0.490, 0.944] (n=10, 95% Wilson)"
    assert Proportion.model_validate_json(proportion.model_dump_json()) == proportion
    with pytest.raises(ValidationError):
        Proportion.model_validate({**proportion.model_dump(), "estimand": "per_attempt"})


@pytest.mark.parametrize(
    ("successes", "trials", "level", "expected"),
    [
        (0, 10000, 0.95, "0.000 [0.000, 0.001] (n=10000, per-attempt, 95% Wilson)"),
        (19999, 20000, 0.95, "0.999950 [0.999716, 0.999992] (n=20000, per-attempt, 95% Wilson)"),
        (6, 20, 0.95, "0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)"),
        (1, 3, 0.9999999, "0.333 [0.011, 0.958] (n=3, per-attempt, 99.99999% Wilson)"),
        (1, 3, 0.95, "0.333 [0.061, 0.793] (n=3, per-attempt, 95% Wilson)"),
        (7, 10, 0.9, "0.700 [0.441, 0.874] (n=10, per-attempt, 90% Wilson)"),
    ],
)
def test_rendering_reviewer_cases(successes: int, trials: int, level: float, expected: str) -> None:
    """Exact renderings for the edge cases: outward bounds, extra digits only when needed."""
    rate = per_attempt(successes, trials, level)
    assert rate.render() == expected
    assert str(rate) == expected
    assert expected.isascii()


def test_per_trial_label() -> None:
    """The per-trial estimand renders as per-trial."""
    rate = Rate.from_counts(6, 30, estimand=Estimand.PER_TRIAL)
    assert rate.render() == "0.200 [0.095, 0.374] (n=30, per-trial, 95% Wilson)"


@pytest.mark.parametrize("level", [0.1, 0.5, 0.8, 0.95, 0.9999999])
def test_printed_interval_always_contains_true_interval(level: float) -> None:
    """For every x <= n <= 60 and n in {10^3, 10^4, 2*10^4} edge counts: containment holds.

    The printed interval contains the computed one, has non-zero width when the computed one
    does, prints 0 or 1 only for values exactly 0 or 1, and the estimate lies inside it.
    """
    cases = [(x, n) for n in range(1, 61) for x in range(n + 1)]
    cases += [(x, n) for n in (1000, 10000, 20000) for x in (0, 1, 2, n - 2, n - 1, n)]
    for successes, trials in cases:
        rate = per_attempt(successes, trials, level)
        estimate, lower, upper = printed(rate.render())
        true_lower, true_upper = Decimal(rate.interval.lower), Decimal(rate.interval.upper)
        assert lower <= true_lower
        assert upper >= true_upper
        assert lower <= estimate <= upper
        if true_lower < true_upper:
            assert lower < upper
        for value, text in ((rate.estimate, estimate), (rate.interval.lower, lower)):
            assert text != 0 or value == 0
            assert text != 1 or value == 1
        assert upper != 0 or rate.interval.upper == 0
        assert upper != 1 or rate.interval.upper == 1


def test_format_estimate_and_interval_rounds_outward_on_exact_binary_value() -> None:
    """Bounds just below and above a 3-decimal boundary still round outward."""
    just_below = 0.145 - 1e-17
    assert format_estimate_and_interval(0.3, just_below, 0.5).startswith("0.300 [0.144,")
    assert format_estimate_and_interval(0.3, 0.1, 0.519).endswith(", 0.520]")


@pytest.mark.parametrize(
    ("level", "label"),
    [
        (0.95, "95%"),
        (0.9, "90%"),
        (0.995, "99.5%"),
        (0.5, "50%"),
        (0.1, "10%"),
        (0.9999999, "99.99999%"),
        (0.57, "57%"),
        (1e-7, "0.00001%"),
    ],
)
def test_level_label_is_exact(level: float, label: str) -> None:
    """The level label is the exact percentage of the level's shortest repr."""
    assert format_level(level) == label
