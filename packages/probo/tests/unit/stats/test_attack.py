# SPDX-License-Identifier: Apache-2.0
"""Attack success per delivered attempt and per trial."""

import json
from collections.abc import Mapping
from typing import cast

import pytest
from pydantic import ValidationError

from probo.schema import EXCLUDED_OUTCOMES, Outcome
from probo.stats import AttackSuccess, Estimand, OutcomeCounts, Rate

DELIVERED = {Outcome.ATTACK_SUCCEEDED: 6, Outcome.ATTACK_FAILED_TARGET_RESISTED: 14}


def test_rates_on_delivered_only_trials_have_equal_counts_and_distinct_estimands() -> None:
    """With no excluded trials both rates are 6 / 20, labelled per-attempt and per-trial."""
    result = AttackSuccess.from_counts(DELIVERED)
    assert result.per_attempt == Rate.from_counts(6, 20, estimand=Estimand.PER_ATTEMPT)
    assert result.per_trial == Rate.from_counts(6, 20, estimand=Estimand.PER_TRIAL)


@pytest.mark.parametrize("excluded", sorted(EXCLUDED_OUTCOMES))
def test_excluded_outcome_changes_per_trial_rate_not_per_attempt(excluded: Outcome) -> None:
    """Adding 10 trials of any excluded outcome keeps per-attempt at 6/20, per-trial at 6/30."""
    baseline = AttackSuccess.from_counts(DELIVERED)
    result = AttackSuccess.from_counts({**DELIVERED, excluded: 10})
    assert result.per_attempt == baseline.per_attempt
    assert result.per_trial is not None
    assert (result.per_trial.successes, result.per_trial.trials) == (6, 30)
    assert baseline.per_attempt is not None
    assert result.per_trial.estimate < baseline.per_attempt.estimate
    assert result.per_trial.interval.upper < baseline.per_attempt.interval.upper


def test_informative_missingness_example_from_docstring() -> None:
    """5 succeeded + 95 target_refused_task: per-attempt 1.000, per-trial 0.050."""
    result = AttackSuccess.from_counts(
        {Outcome.ATTACK_SUCCEEDED: 5, Outcome.TARGET_REFUSED_TASK: 95}
    )
    assert result.per_attempt is not None
    assert result.per_trial is not None
    assert result.per_attempt.estimate == 1.0
    assert result.per_trial.estimate == 0.05
    assert "1.000 [" in result.render().splitlines()[0]


def test_all_excluded_gives_absent_per_attempt_and_zero_per_trial() -> None:
    """No delivered trial: per-attempt is None, not 0; per-trial is 0 / N."""
    result = AttackSuccess.from_counts({Outcome.NOT_DELIVERED: 4, Outcome.PROVIDER_ERROR: 1})
    assert result.per_attempt is None
    assert result.per_trial is not None
    assert (result.per_trial.successes, result.per_trial.trials) == (0, 5)
    assert result.render().splitlines()[0].endswith("absent (denominator is 0)")


def test_no_trials_gives_both_rates_absent() -> None:
    """Zero trials: both rates are None and the rendering says so."""
    result = AttackSuccess.from_counts({})
    assert result.per_attempt is None
    assert result.per_trial is None
    lines = result.render().splitlines()
    assert all(line.endswith("absent (denominator is 0)") for line in lines[:2])
    assert "nan" not in result.render().lower()


def test_counts_always_sum_to_trials() -> None:
    """Every outcome is reported, zeros included, and the counts sum to the trial count."""
    mapping = {outcome: index + 1 for index, outcome in enumerate(Outcome)}
    result = AttackSuccess.from_counts(mapping)
    assert result.counts.total == sum(mapping.values())
    assert result.per_trial is not None
    assert result.per_trial.trials == result.counts.total
    assert result.per_attempt is not None
    assert result.counts.excluded + result.per_attempt.trials == result.counts.total
    assert {outcome: result.counts[outcome] for outcome in Outcome} == mapping
    sparse = AttackSuccess.from_counts({Outcome.GRADER_ERROR: 2})
    assert [sparse.counts[o] for o in Outcome].count(0) == len(Outcome) - 1


def test_outcome_counts_fields_track_the_outcome_enum() -> None:
    """OutcomeCounts has exactly one field per Outcome value."""
    assert list(OutcomeCounts.model_fields) == [o.value for o in Outcome]


def test_render_shows_both_rates_and_every_outcome() -> None:
    """Three ASCII lines: per-attempt, per-trial, and all ten counts with totals."""
    text = AttackSuccess.from_counts({**DELIVERED, Outcome.NOT_DELIVERED: 10}).render()
    assert text.isascii()
    attempt, trial, outcomes = text.splitlines()
    assert attempt.startswith("per attempt (attack_succeeded / (attack_succeeded")
    assert attempt.endswith("0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)")
    assert trial.startswith("per trial (attack_succeeded / all trials")
    assert trial.endswith("0.200 [0.095, 0.374] (n=30, per-trial, 95% Wilson)")
    assert outcomes.startswith("outcomes (n=30, excluded=10): ")
    assert all(f"{o}=" in outcomes for o in Outcome)


def test_level_is_applied_to_both_rates() -> None:
    """The requested level reaches both intervals."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.HARNESS_ERROR: 5}, level=0.5)
    assert result.per_attempt is not None
    assert result.per_trial is not None
    assert result.per_attempt.level == result.per_trial.level == 0.5


def test_only_counts_and_level_are_stored_but_rates_are_dumped() -> None:
    """The rates are computed; dumps still carry them, and a dump loads back equal."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.GRADER_UNCERTAIN: 3})
    assert set(AttackSuccess.model_fields) == {"counts", "level"}
    dumped = json.loads(result.model_dump_json())
    assert dumped["per_attempt"]["estimand"] == "per_attempt"
    assert dumped["per_trial"]["trials"] == 23
    assert AttackSuccess.model_validate_json(result.model_dump_json()) == result
    assert AttackSuccess.model_validate(result.model_dump()) == result
    assert AttackSuccess.model_validate({"counts": dumped["counts"], "level": 0.95}) == result
    empty = AttackSuccess.from_counts({})
    assert AttackSuccess.model_validate_json(empty.model_dump_json()) == empty


def test_tampered_rates_in_json_are_refused() -> None:
    """Supplied rates that the counts do not produce never silently win on load."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.NOT_DELIVERED: 10})
    dumped = json.loads(result.model_dump_json())
    flattering = {**dumped, "per_trial": dumped["per_attempt"]}
    with pytest.raises(ValidationError, match="per_trial"):
        AttackSuccess.model_validate_json(json.dumps(flattering))
    with pytest.raises(ValidationError, match="per_attempt"):
        AttackSuccess.model_validate_json(json.dumps({**dumped, "per_attempt": None}))
    relabelled = {**dumped, "per_trial": {**dumped["per_trial"], "estimand": "per_attempt"}}
    with pytest.raises(ValidationError, match="per_trial"):
        AttackSuccess.model_validate_json(json.dumps(relabelled))
    inner = {**dumped, "per_trial": {**dumped["per_trial"], "estimate": 0.3}}
    with pytest.raises(ValidationError, match="estimate"):
        AttackSuccess.model_validate_json(json.dumps(inner))


def test_model_copy_revalidates() -> None:
    """model_copy(update=...) cannot swap a rate or set an invalid count or level."""
    result = AttackSuccess.from_counts({**DELIVERED, Outcome.NOT_DELIVERED: 10})
    with pytest.raises(ValidationError, match="per_trial"):
        result.model_copy(update={"per_trial": result.per_attempt})
    with pytest.raises(ValidationError, match="level"):
        result.model_copy(update={"level": 1.5})
    with pytest.raises(ValidationError):
        result.counts.model_copy(update={"attack_succeeded": -5})
    with pytest.raises(ValidationError):
        result.counts.model_copy(update={"attack_succeeded": 2.0})
    moved = result.model_copy(
        update={"counts": result.counts.model_copy(update={"not_delivered": 0})}
    )
    assert moved == AttackSuccess.from_counts(DELIVERED)


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


@pytest.mark.parametrize("level", [0.0, 1.0, 1.5, -0.1, float("nan")])
def test_level_is_validated_eagerly_with_or_without_trials(level: float) -> None:
    """An invalid level is refused at construction, even when no interval is computed."""
    with pytest.raises(ValidationError, match="level"):
        AttackSuccess.from_counts({}, level=level)
    with pytest.raises(ValidationError, match="level"):
        AttackSuccess.model_validate({"counts": {}, "level": level})
    with pytest.raises(ValidationError, match="level"):
        AttackSuccess.from_counts(DELIVERED, level=level)


def test_result_is_frozen() -> None:
    """Counts and level cannot be assigned after construction."""
    result = AttackSuccess.from_counts(DELIVERED)
    with pytest.raises(ValidationError):
        result.counts.__setattr__("attack_succeeded", 20)
    with pytest.raises(ValidationError):
        result.__setattr__("level", 0.5)
