# SPDX-License-Identifier: Apache-2.0
"""Three-valued check results: bool or unscored value, and the string under one key."""

import math

import pytest
from inspect_ai.scorer import Score

from probo.checks import (
    NOT_APPLICABLE_REASON,
    RESULT_KEY,
    CheckResult,
    check_result,
    check_score,
)


@pytest.mark.parametrize(
    ("result", "expected"),
    [(True, CheckResult.TRUE), (False, CheckResult.FALSE)],
)
def test_true_and_false_are_bool_values(result: bool, expected: CheckResult) -> None:
    """True and false are bool values with the matching string, and no reason."""
    score = check_score(result, "why", {"n": 1})
    assert score.value is result
    assert score.reason is None
    assert score.explanation == "why"
    assert score.metadata == {"n": 1, RESULT_KEY: expected.value}
    assert check_result(score) is expected


def test_not_applicable_is_unscored_with_its_string() -> None:
    """Not applicable is NaN with reason `not_applicable`, and the string says so."""
    score = check_score(None, "no watched address")
    assert isinstance(score.value, float)
    assert math.isnan(score.value)
    assert score.reason == NOT_APPLICABLE_REASON
    assert score.metadata == {RESULT_KEY: "not_applicable"}
    assert check_result(score) is CheckResult.NOT_APPLICABLE


def test_result_strings_are_plain() -> None:
    """The recorded strings are exactly the documented ones."""
    assert [r.value for r in CheckResult] == ["true", "false", "not_applicable"]


def test_metadata_is_copied_not_changed() -> None:
    """The caller's mapping is not modified."""
    metadata = {"n": 1}
    check_score(True, "why", metadata)
    assert metadata == {"n": 1}


def test_reserved_key_in_metadata_is_refused() -> None:
    """Metadata may not set the result key itself."""
    with pytest.raises(ValueError, match="reserved key"):
        check_score(True, "why", {RESULT_KEY: "false"})


@pytest.mark.parametrize("metadata", [None, {}, {RESULT_KEY: "maybe"}, {RESULT_KEY: True}])
def test_reading_a_score_without_a_valid_result_fails(metadata: dict[str, object] | None) -> None:
    """A score not made by `check_score` is not silently read as some result."""
    with pytest.raises(ValueError, match="no check result"):
        check_result(Score(value=True, metadata=metadata))
