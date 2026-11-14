# SPDX-License-Identifier: Apache-2.0
"""Wilson score interval for a binomial proportion."""

import math
from statistics import NormalDist

from pydantic import BaseModel, ConfigDict, model_validator


def check_counts(successes: int, trials: int) -> None:
    """Raise unless both are ints with trials >= 1 and 0 <= successes <= trials.

    ``TypeError`` for a non-int (``bool`` included, though it subclasses ``int``), otherwise
    ``ValueError``.
    """
    for name, value in (("successes", successes), ("trials", trials)):
        if type(value) is not int:
            raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if trials <= 0:
        raise ValueError(f"trials must be >= 1, got {trials}")
    if not 0 <= successes <= trials:
        raise ValueError(f"successes must be in [0, trials={trials}], got {successes}")


def critical_value(level: float) -> float:
    """Two-sided normal critical value z = Phi^-1(1 - (1 - level) / 2) for 0 < level < 1.

    Phi^-1 is ``statistics.NormalDist().inv_cdf``. It is evaluated as -Phi^-1((1 - level) / 2),
    which is equal by symmetry and avoids 1 - (1 - level) / 2 rounding to 1.0 for levels
    within one ulp of 1. Raises ``ValueError`` for a level outside the open interval (0, 1),
    including NaN.
    """
    if not 0.0 < level < 1.0:
        raise ValueError(f"level must be in the open interval (0, 1), got {level}")
    return -NormalDist().inv_cdf((1.0 - level) / 2.0)


class Interval(BaseModel):
    """A closed interval [lower, upper] with 0 <= lower <= upper <= 1."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    lower: float
    """Lower bound."""
    upper: float
    """Upper bound."""

    @model_validator(mode="after")
    def _bounds_are_ordered_in_unit_interval(self) -> "Interval":
        if not 0.0 <= self.lower <= self.upper <= 1.0:
            raise ValueError(
                f"interval must satisfy 0 <= lower <= upper <= 1, got [{self.lower}, {self.upper}]"
            )
        return self


def wilson_interval(successes: int, trials: int, level: float = 0.95) -> Interval:
    """Two-sided Wilson score interval for a binomial proportion.

    With x = successes, n = trials and z = ``critical_value(level)``:

        center = (x + z^2 / 2) / (n + z^2)
        half   = z * sqrt(x * (n - x) / n + z^2 / 4) / (n + z^2)
        [lower, upper] = [center - half, center + half]

    This is algebraically the textbook form with p = x / n,
    (p + z^2/(2n)) / (1 + z^2/n) +- z * sqrt(p(1-p)/n + z^2/(4n^2)) / (1 + z^2/n).

    The bounds at the edges are set exactly rather than left to rounding: x = 0 gives
    lower = 0.0 (and upper = z^2 / (n + z^2)); x = n gives upper = 1.0 (and
    lower = n / (n + z^2)). Interior bounds are clamped to [0, 1] for float safety only;
    analytically they already lie strictly inside (0, 1).

    Raises ``TypeError`` for non-int counts and ``ValueError`` for trials <= 0, successes
    outside [0, trials], or level outside (0, 1).
    """
    check_counts(successes, trials)
    z = critical_value(level)
    z2 = z * z
    denominator = trials + z2
    center = (successes + z2 / 2.0) / denominator
    half = z * math.sqrt(successes * (trials - successes) / trials + z2 / 4.0) / denominator
    lower = 0.0 if successes == 0 else max(center - half, 0.0)
    upper = 1.0 if successes == trials else min(center + half, 1.0)
    return Interval(lower=lower, upper=upper)
