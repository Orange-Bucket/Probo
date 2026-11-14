# SPDX-License-Identifier: Apache-2.0
"""Proportions and labelled rates that always carry their trial count and Wilson interval."""

from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from enum import StrEnum
from typing import Annotated, ClassVar, Self

from pydantic import Field, computed_field, model_validator

from probo.stats.base import FrozenModel, require_close
from probo.stats.wilson import Interval, check_counts, critical_value, wilson_interval


class Estimand(StrEnum):
    """What an attack success rate estimates.

    s = #attack_succeeded, r = #attack_failed_target_resisted, N = all trials
    (see ``probo.schema.Outcome``).
    """

    PER_ATTEMPT = "per_attempt"
    """P(one delivered, graded attempt produces the verified side effect); s / (s + r)."""

    PER_TRIAL = "per_trial"
    """P(one trial produces the verified side effect), excluded trials as failures; s / N."""


def format_level(level: float) -> str:
    """``level`` as the exact percentage of its shortest repr.

    0.95 -> ``95%``, 0.995 -> ``99.5%``, 0.9999999 -> ``99.99999%``; never rounded.
    """
    percent = (Decimal(repr(level)) * 100).normalize()
    return f"{percent:f}%"


def format_estimate_and_interval(estimate: float, lower: float, upper: float) -> str:
    """``E [L, U]`` with L rounded down, U rounded up and E rounded to nearest, in decimals.

    The same number of decimal places d is used for all three, starting at 3 and increased
    until no value that is not exactly 0 prints as 0 and no value that is not exactly 1
    prints as 1. Rounding acts on the exact binary value of each float, so the printed
    interval always contains [lower, upper], and has non-zero width whenever lower < upper.
    """
    with localcontext() as context:
        context.prec = 64
        places = 3
        while True:
            step = Decimal(1).scaleb(-places)
            texts = [
                Decimal(estimate).quantize(step, rounding=ROUND_HALF_EVEN),
                Decimal(lower).quantize(step, rounding=ROUND_FLOOR),
                Decimal(upper).quantize(step, rounding=ROUND_CEILING),
            ]
            if all(
                (text != 0 or value == 0) and (text != 1 or value == 1)
                for value, text in zip((estimate, lower, upper), texts, strict=True)
            ):
                return f"{texts[0]} [{texts[1]}, {texts[2]}]"
            places += 1


class _Binomial(FrozenModel):
    """Shared fields, derived values and checks of ``Proportion`` and ``Rate``."""

    DERIVED: ClassVar[tuple[str, ...]] = ("estimate", "interval")

    successes: int
    """x, the number of trials counted as successes."""
    trials: int
    """n >= 1, the number of trials in the denominator."""
    level: float
    """Confidence level of ``interval``, in (0, 1)."""

    @model_validator(mode="after")
    def _counts_and_level_are_valid(self) -> Self:
        check_counts(self.successes, self.trials)
        critical_value(self.level)
        return self

    @computed_field
    @property
    def estimate(self) -> float:
        """Point estimate x / n, computed from the counts."""
        return self.successes / self.trials

    @computed_field
    @property
    def interval(self) -> Interval:
        """``wilson_interval(successes, trials, level)``, computed from the stored fields."""
        return wilson_interval(self.successes, self.trials, self.level)

    def check_derived(self, name: str, value: object) -> None:
        """Accept a supplied ``estimate`` or ``interval`` only within tolerance of the computed."""
        if name == "estimate":
            require_close(name, value, self.estimate)
            return
        supplied = Interval.model_validate(value)
        require_close("interval.lower", supplied.lower, self.interval.lower)
        require_close("interval.upper", supplied.upper, self.interval.upper)

    def _render(self, label: str | None) -> str:
        interval = self.interval
        parts = [f"n={self.trials}"]
        if label is not None:
            parts.append(label)
        parts.append(f"{format_level(self.level)} Wilson")
        numbers = format_estimate_and_interval(self.estimate, interval.lower, interval.upper)
        return f"{numbers} ({', '.join(parts)})"


class Proportion(_Binomial):
    """A binomial proportion x / n with its two-sided Wilson interval at ``level``.

    Stores only ``successes``, ``trials`` and ``level``; ``estimate`` and ``interval`` are
    computed from them and included in dumps. Loading accepts those derived keys only when
    they agree with the recomputed values (see ``FrozenModel``).
    """

    @classmethod
    def from_counts(cls, successes: int, trials: int, *, level: float = 0.95) -> "Proportion":
        """Return x / n with its Wilson interval; raises for counts or level out of range."""
        return cls(successes=successes, trials=trials, level=level)

    def render(self) -> str:
        """ASCII text such as ``0.800 [0.490, 0.944] (n=10, 95% Wilson)``."""
        return self._render(None)

    def __str__(self) -> str:
        return self.render()


class Rate(_Binomial):
    """An attack success rate: a binomial proportion labelled with what it estimates.

    Stores ``successes``, ``trials``, ``level`` and ``estimand``; ``estimate = successes /
    trials`` and ``interval = wilson_interval(successes, trials, level)`` are computed and
    included in dumps. Loading accepts those derived keys only when they agree with the
    recomputed values (see ``FrozenModel``).
    """

    estimand: Annotated[Estimand, Field(strict=False)]
    """What the rate estimates. Its string value is accepted on input (it is a StrEnum)."""

    @classmethod
    def from_counts(
        cls, successes: int, trials: int, *, estimand: Estimand, level: float = 0.95
    ) -> "Rate":
        """Return the rate x / n labelled ``estimand``; raises for invalid counts or level."""
        return cls(successes=successes, trials=trials, level=level, estimand=estimand)

    @property
    def label(self) -> str:
        """``per-attempt`` or ``per-trial``."""
        return self.estimand.value.replace("_", "-")

    def render(self) -> str:
        """ASCII text such as ``0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)``."""
        return self._render(self.label)

    def __str__(self) -> str:
        return self.render()


def render_optional(value: Proportion | Rate | None) -> str:
    """``value.render()``, or ``absent (denominator is 0)`` when ``value`` is None."""
    return "absent (denominator is 0)" if value is None else value.render()
