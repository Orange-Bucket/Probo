# SPDX-License-Identifier: Apache-2.0
"""Attack success under the default and conservative denominator policies."""

from collections.abc import Mapping
from typing import cast

import pytest
from pydantic import ValidationError

from probo.schema import EXCLUDED_OUTCOMES, Outcome
from probo.stats import AttackSuccess, Estimand, OutcomeCounts, Rate

DELIVERED = {Outcome.ATTACK_SUCCEEDED: 6, Outcome.ATTACK_FAILED_TARGET_RESISTED: 14}


def test_default_and_conservative_rates_on_delivered_only_trials_agree() -> None:
    """With no excluded trials both policies give s / (s + r) = 6 / 20."""
    result = AttackSuccess.from_counts(DELIVERED)
    expected = Rate.from_counts(6, 20, estimand=Estimand.PER_ATTEMPT)
    assert result.default == expected
    assert result.conservative == expected


@pytest.mark.parametrize("excluded", sorted(EXCLUDED_OUTCOMES))
def test_excluded_outcome_changes_conservative_rate_not_default(excluded: Outcome) -> None:
    """Adding 10 trials of any excluded outcome leaves default at 6/20 and drops conservative."""
    baseline = AttackSuccess.from_counts(DELIVERED)
    result = AttackSuccess.from_counts({**DELIVERED, excluded: 10})
    assert result.default == baseline.default
    assert result.conservative is not None
    assert (result.conservative.successes, result.conservative.trials) == (6, 30)
    assert baseline.default is not None
    assert result.conservative.estimate < baseline.default.estimate
    assert result.conservative.interval.upper < baseline.default.interval.upper


def test_all_excluded_gives_absent_default_and_zero_conservative() -> None:
    """No delivered trial: the default rate is None, not 0; conservative is 0 / N."""
    result = AttackSuccess.from_counts({Outcome.NOT_DELIVERED: 4, Outcome.PROVIDER_ERROR: 1})
    assert result.default is None
    assert result.conservative is not None
    assert (result.conservative.successes, result.conservative.trials) == (0, 5)
    assert "absent (denominator is 0)" in result.render().splitlines()[0]


def test_no_trials_gives_both_rates_absent() -> None:
    """Zero trials: both rates are None and the rendering says so."""
    result = AttackSuccess.from_counts({})
    assert result.default is None
    assert result.conservative is None
    lines = result.render().splitlines()
    assert all("absent (denominator is 0)" in line for line in lines[:2])
    assert "nan" not in result.render().lower()


def test_counts_always_sum_to_trials() -> None:
    """Every outcome is reported, zeros included, and the counts sum to the trial count."""
    mapping = {outcome: index + 1 for index, outcome in enumerate(Outcome)}
    result = AttackSuccess.from_counts(mapping)
    assert result.counts.total == sum(mapping.values())
    assert result.conservative is not None
    assert result.conservative.trials == result.counts.total
    assert result.default is not None
    assert result.counts.excluded + result.default.trials == result.counts.total
    assert {outcome: result.counts[outcome] for outcome in Outcome} == mapping
    sparse = AttackSuccess.from_counts({Outcome.GRADER_ERROR: 2})
    assert [sparse.counts[o] for o in Outcome].count(0) == len(Outcome) - 1


def test_outcome_counts_fields_track_the_outcome_enum() -> None:
    """OutcomeCounts has exactly one field per Outcome value."""
    assert list(OutcomeCounts.model_fields) == [o.value for o in Outcome]


def test_render_shows_both_policies_and_every_outcome() -> None:
    """Three ASCII lines: default, conservative, and all ten counts with totals."""
    text = AttackSuccess.from_counts({**DELIVERED, Outcome.NOT_DELIVERED: 10}).render()
    assert text.isascii()
    default, conservative, outcomes = text.splitlines()
    assert default.endswith("0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)")
    assert conservative.startswith("conservative (attack_succeeded / all trials")
    assert conservative.endswith("0.200 [0.095, 0.373] (n=30, per-attempt, 95% Wilson)")
    assert outcomes.startswith("outcomes (n=30, excluded=10): ")
    assert all(f"{o}=" in outcomes for o in Outcome)


def test_level_is_applied_to_both_rates() -> None:
    """The requested level reaches both intervals."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.HARNESS_ERROR: 5}, level=0.9)
    assert result.default is not None
    assert result.conservative is not None
    assert result.default.level == result.conservative.level == 0.9


def test_round_trips_through_json() -> None:
    """A saved result loads back equal."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.GRADER_UNCERTAIN: 3})
    assert AttackSuccess.model_validate_json(result.model_dump_json()) == result


def test_rejects_rates_inconsistent_with_counts() -> None:
    """A stored default or conservative rate that the counts do not produce is refused."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.NOT_DELIVERED: 10})
    flattering = result.model_copy(update={"conservative": result.default}).model_dump()
    with pytest.raises(ValidationError, match="computed from counts"):
        AttackSuccess.model_validate(flattering)
    with pytest.raises(ValidationError, match="computed from counts"):
        AttackSuccess.model_validate({**result.model_dump(), "default": None})


def test_rejects_negative_non_int_and_unknown_counts() -> None:
    """Counts must be non-negative ints keyed by a known outcome."""
    with pytest.raises(ValidationError):
        AttackSuccess.from_counts({Outcome.ATTACK_SUCCEEDED: -1})
    with pytest.raises(ValidationError):
        OutcomeCounts.model_validate({"attack_succeeded": 1.0})
    with pytest.raises(ValidationError):
        OutcomeCounts.model_validate({"attack_succeeded": True})
    with pytest.raises(ValidationError):
        OutcomeCounts.model_validate({"attack_defended": 1})
    with pytest.raises(ValueError, match="is not a valid Outcome"):
        OutcomeCounts.from_mapping(cast(Mapping[Outcome, int], {"attack_defended": 1}))


def test_rejects_level_outside_open_unit_interval_even_without_trials() -> None:
    """The level is validated even when no interval is computed."""
    with pytest.raises(ValueError, match="level"):
        AttackSuccess.from_counts({}, level=1.0)


def test_result_is_frozen() -> None:
    """Counts and rates cannot be changed after construction."""
    result = AttackSuccess.from_counts(DELIVERED)
    with pytest.raises(ValidationError):
        result.counts.__setattr__("attack_succeeded", 20)
    with pytest.raises(ValidationError):
        result.__setattr__("default", None)
