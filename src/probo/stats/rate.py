# SPDX-License-Identifier: Apache-2.0
"""Proportions and labelled rates that always carry their trial count and Wilson interval."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

from probo.stats.wilson import Interval, check_counts, wilson_interval


class Estimand(StrEnum):
    """What an attack success rate estimates.

    Let p be the probability that one delivered attempt produces the verified side effect.
    The ``_K`` estimands are defined over groups of k attempts at the same task; their trials
    are groups, not attempts. Probo computes only ``PER_ATTEMPT`` from trial outcomes; the
    other two are labels for rates whose group counts were formed elsewhere.
    """

    PER_ATTEMPT = "per_attempt"
    """p, estimated as x / n over n delivered, graded attempts of which x succeeded."""

    AT_LEAST_ONE_OF_K = "at_least_one_of_k"
    """ASR@k: P(at least one of k attempts succeeds); equals 1 - (1 - p)^k only if i.i.d."""

    ALL_OF_K = "all_of_k"
    """ASR^k: P(all k attempts succeed); equals p^k only if the attempts are i.i.d."""


def _format_level(level: float) -> str:
    return f"{level * 100:g}%"


class _Binomial(BaseModel):
    """Shared fields and checks of ``Proportion`` and ``Rate``."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    successes: int
    """x, the number of trials counted as successes."""
    trials: int
    """n >= 1, the number of trials in the denominator."""
    level: float
    """Confidence level of ``interval``, in (0, 1)."""
    estimate: float
    """Point estimate x / n."""
    interval: Interval
    """``wilson_interval(successes, trials, level)``."""

    @model_validator(mode="after")
    def _derived_fields_match_counts(self) -> "_Binomial":
        check_counts(self.successes, self.trials)
        if self.estimate != self.successes / self.trials:
            raise ValueError(
                f"estimate {self.estimate} != successes / trials = {self.successes}/{self.trials}"
            )
        expected = wilson_interval(self.successes, self.trials, self.level)
        if self.interval != expected:
            raise ValueError(f"interval {self.interval} != Wilson interval {expected}")
        return self

    def _render(self, label: str | None) -> str:
        parts = [f"n={self.trials}"]
        if label is not None:
            parts.append(label)
        parts.append(f"{_format_level(self.level)} Wilson")
        return (
            f"{self.estimate:.3f} [{self.interval.lower:.3f}, {self.interval.upper:.3f}]"
            f" ({', '.join(parts)})"
        )


class Proportion(_Binomial):
    """A binomial proportion x / n with its two-sided Wilson interval at ``level``.

    Construction checks that ``estimate == successes / trials`` and ``interval ==
    wilson_interval(successes, trials, level)`` exactly, so a stored or deserialised
    proportion cannot disagree with its counts. Build one with ``from_counts``.
    """

    @classmethod
    def from_counts(cls, successes: int, trials: int, *, level: float = 0.95) -> "Proportion":
        """Return x / n with its Wilson interval; raises for counts or level out of range."""
        interval = wilson_interval(successes, trials, level)
        return cls(
            successes=successes,
            trials=trials,
            level=level,
            estimate=successes / trials,
            interval=interval,
        )

    def render(self) -> str:
        """ASCII text such as ``0.800 [0.490, 0.943] (n=10, 95% Wilson)``."""
        return self._render(None)

    def __str__(self) -> str:
        return self.render()


class Rate(_Binomial):
    """An attack success rate: a binomial proportion labelled with what it estimates.

    ``estimate = successes / trials`` and ``interval = wilson_interval(successes, trials,
    level)``, both checked exactly on construction. For ``Estimand.PER_ATTEMPT`` the trials are
    attempts and ``k`` must be None. For ``AT_LEAST_ONE_OF_K`` and ``ALL_OF_K`` the trials are
    groups of ``k`` attempts (k >= 1), a success is a group meeting the estimand, and ``k`` is
    required. Build one with ``from_counts``.
    """

    estimand: Estimand
    """What the rate estimates."""
    k: int | None = None
    """Group size for the ``_K`` estimands; None for ``PER_ATTEMPT``."""

    @model_validator(mode="after")
    def _k_matches_estimand(self) -> "Rate":
        if self.estimand is Estimand.PER_ATTEMPT:
            if self.k is not None:
                raise ValueError(f"k must be None for {self.estimand}, got {self.k}")
        elif self.k is None or self.k < 1:
            raise ValueError(f"{self.estimand} requires an int k >= 1, got {self.k}")
        return self

    @classmethod
    def from_counts(
        cls,
        successes: int,
        trials: int,
        *,
        estimand: Estimand,
        k: int | None = None,
        level: float = 0.95,
    ) -> "Rate":
        """Return the rate x / n labelled ``estimand``; raises for invalid counts, level or k."""
        interval = wilson_interval(successes, trials, level)
        return cls(
            successes=successes,
            trials=trials,
            level=level,
            estimate=successes / trials,
            interval=interval,
            estimand=estimand,
            k=k,
        )

    @property
    def label(self) -> str:
        """``per-attempt``, ``at-least-one-of-<k>`` or ``all-of-<k>``."""
        if self.estimand is Estimand.PER_ATTEMPT:
            return "per-attempt"
        if self.estimand is Estimand.AT_LEAST_ONE_OF_K:
            return f"at-least-one-of-{self.k}"
        return f"all-of-{self.k}"

    def render(self) -> str:
        """ASCII text such as ``0.300 [0.145, 0.519] (n=20, per-attempt, 95% Wilson)``."""
        return self._render(self.label)

    def __str__(self) -> str:
        return self.render()


def render_optional(value: Proportion | Rate | None) -> str:
    """``value.render()``, or ``absent (denominator is 0)`` when ``value`` is None."""
    return "absent (denominator is 0)" if value is None else value.render()
