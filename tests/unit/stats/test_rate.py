# SPDX-License-Identifier: Apache-2.0
"""Proportion and Rate: derived fields, estimand labels, rendering and validation."""

import pytest
from pydantic import ValidationError

from probo.stats import Estimand, Interval, Proportion, Rate, wilson_interval


def per_attempt(successes: int, trials: int, level: float = 0.95) -> Rate:
    return Rate.from_counts(successes, trials, estimand=Estimand.PER_ATTEMPT, level=level)


def test_rate_carries_counts_estimate_interval_level_and_estimand() -> None:
    """from_counts fills estimate = x / n and the Wilson interval at the given level."""
    rate = per_attempt(6, 20, level=0.9)
    assert (rate.successes, rate.trials, rate.level) == (6, 20, 0.9)
    assert rate.estimate == 0.3
    assert rate.interval == wilson_interval(6, 20, 0.9)
    assert rate.estimand is Estimand.PER_ATTEMPT
    assert rate.k is None


def test_rate_renders_compact_ascii_with_count_interval_and_label() -> None:
    """The rendering names the estimate, interval, n, estimand and interval method."""
    assert per_attempt(6, 20).render() == "0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)"
    assert str(per_attempt(7, 10, level=0.9)) == (
        "0.700 [0.442, 0.873] (n=10, per-attempt, 90% Wilson)"
    )
    assert per_attempt(1, 3, level=0.995).render().endswith("99.5% Wilson)")
    assert per_attempt(6, 20).render().isascii()


def test_k_estimands_are_labels_that_require_k() -> None:
    """ASR@k and ASR^k need k; they render the group size, and per-attempt forbids k."""
    at_least = Rate.from_counts(4, 10, estimand=Estimand.AT_LEAST_ONE_OF_K, k=5)
    all_of = Rate.from_counts(1, 10, estimand=Estimand.ALL_OF_K, k=3)
    assert "(n=10, at-least-one-of-5, 95% Wilson)" in at_least.render()
    assert "(n=10, all-of-3, 95% Wilson)" in all_of.render()
    for estimand in (Estimand.AT_LEAST_ONE_OF_K, Estimand.ALL_OF_K):
        with pytest.raises(ValidationError, match="requires an int k"):
            Rate.from_counts(1, 10, estimand=estimand)
        with pytest.raises(ValidationError, match="requires an int k"):
            Rate.from_counts(1, 10, estimand=estimand, k=0)
    with pytest.raises(ValidationError, match="k must be None"):
        Rate.from_counts(1, 10, estimand=Estimand.PER_ATTEMPT, k=2)


def test_estimand_values() -> None:
    """The three estimands and their serialised values."""
    assert [e.value for e in Estimand] == ["per_attempt", "at_least_one_of_k", "all_of_k"]


def test_rate_cannot_be_built_without_trials_interval_or_estimand() -> None:
    """Every field is required: a bare estimate is not a Rate."""
    with pytest.raises(ValidationError):
        Rate.model_validate({"estimate": 0.3, "estimand": "per_attempt"})
    with pytest.raises(ValidationError):
        Rate.model_validate({"successes": 6, "trials": 20, "level": 0.95, "estimate": 0.3})


def test_rate_rejects_estimate_or_interval_inconsistent_with_counts() -> None:
    """A stored estimate or interval that disagrees with the counts is refused."""
    good = per_attempt(6, 20)
    fields = good.model_dump()
    with pytest.raises(ValidationError, match="estimate"):
        Rate.model_validate({**fields, "estimate": 0.5})
    with pytest.raises(ValidationError, match="Wilson"):
        Rate.model_validate({**fields, "interval": {"lower": 0.2, "upper": 0.4}})
    with pytest.raises(ValidationError, match="Wilson"):
        Rate.model_validate({**fields, "level": 0.9})


def test_rate_round_trips_through_json() -> None:
    """Serialised floats re-validate exactly, so a saved rate loads back equal."""
    for rate in (per_attempt(6, 20), per_attempt(0, 50, 0.99), per_attempt(13, 13)):
        assert Rate.model_validate_json(rate.model_dump_json()) == rate


def test_rate_is_frozen_and_rejects_unknown_fields() -> None:
    """Rates are immutable and do not accept extra keys."""
    rate = per_attempt(6, 20)
    with pytest.raises(ValidationError):
        rate.__setattr__("successes", 7)
    with pytest.raises(ValidationError):
        Rate.model_validate({**rate.model_dump(), "accuracy": 0.9})


@pytest.mark.parametrize(("successes", "trials"), [(0, 0), (-1, 5), (6, 5)])
def test_rate_rejects_invalid_counts(successes: int, trials: int) -> None:
    """Zero trials and successes outside [0, trials] raise ValueError."""
    with pytest.raises(ValueError):
        per_attempt(successes, trials)


def test_rate_rejects_bool_counts_on_validation() -> None:
    """Strict validation does not coerce bools or floats into counts."""
    fields = per_attempt(1, 1).model_dump()
    with pytest.raises(ValidationError):
        Rate.model_validate({**fields, "successes": True})
    with pytest.raises(ValidationError):
        Rate.model_validate({**fields, "trials": 1.0})


def test_proportion_has_no_estimand_and_renders_without_label() -> None:
    """A Proportion is a bare x / n with Wilson interval, rendered without an estimand."""
    proportion = Proportion.from_counts(8, 10)
    assert proportion.estimate == 0.8
    assert proportion.interval == wilson_interval(8, 10)
    assert proportion.render() == "0.800 [0.490, 0.943] (n=10, 95% Wilson)"
    assert Proportion.model_validate_json(proportion.model_dump_json()) == proportion
    with pytest.raises(ValidationError):
        Proportion.model_validate({**proportion.model_dump(), "estimand": "per_attempt"})


def test_proportion_rejects_level_outside_open_unit_interval() -> None:
    """level 0 or 1 is refused."""
    for level in (0.0, 1.0):
        with pytest.raises(ValueError, match="level"):
            Proportion.from_counts(1, 2, level=level)


def test_interval_type_is_shared() -> None:
    """Rate.interval is the public Interval type."""
    assert isinstance(per_attempt(1, 2).interval, Interval)
