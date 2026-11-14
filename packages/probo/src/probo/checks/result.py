# SPDX-License-Identifier: Apache-2.0
"""Three-valued check results (true, false, not applicable) as Inspect scores.

Convention for every check scorer in Probo:

- true and false are a bool `Score.value`;
- not applicable is `Score.unscored(reason="not_applicable")`, whose value is NaN, which
  Inspect's metrics and reducers skip;
- in all three cases `Score.metadata[RESULT_KEY]` holds the result as a plain string
  (`"true"`, `"false"` or `"not_applicable"`), so a log reader never has to compare a value
  against NaN.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any, Final

from inspect_ai.scorer import Score

RESULT_KEY: Final = "result"
"""Key of `Score.metadata` that holds the `CheckResult` string."""

NOT_APPLICABLE_REASON: Final = "not_applicable"
"""`Score.reason` of a not-applicable score."""


class CheckResult(StrEnum):
    """The outcome of one check on one sample."""

    TRUE = "true"
    """The checked condition holds."""

    FALSE = "false"
    """The checked condition does not hold."""

    NOT_APPLICABLE = "not_applicable"
    """The check does not apply to this sample; the score is excluded from aggregates."""


def check_score(
    result: bool | None, explanation: str, metadata: Mapping[str, Any] | None = None
) -> Score:
    """The score for a check result: `True`, `False`, or `None` for not applicable.

    `metadata` is copied and gains `RESULT_KEY`.

    Raises:
        ValueError: If `metadata` already has the `RESULT_KEY` key.
    """
    if metadata is not None and RESULT_KEY in metadata:
        raise ValueError(f"metadata must not set the reserved key {RESULT_KEY!r}")
    match result:
        case True:
            outcome = CheckResult.TRUE
        case False:
            outcome = CheckResult.FALSE
        case None:
            outcome = CheckResult.NOT_APPLICABLE
    full = {**(metadata or {}), RESULT_KEY: outcome.value}
    if result is None:
        return Score.unscored(reason=NOT_APPLICABLE_REASON, explanation=explanation, metadata=full)
    return Score(value=result, explanation=explanation, metadata=full)


def check_result(score: Score) -> CheckResult:
    """The result recorded in a score made by `check_score`.

    Raises:
        ValueError: If the score has no valid `RESULT_KEY` entry.
    """
    raw = (score.metadata or {}).get(RESULT_KEY)
    try:
        return CheckResult(raw)
    except ValueError:
        raise ValueError(f"score has no check result under {RESULT_KEY!r}: {raw!r}") from None
