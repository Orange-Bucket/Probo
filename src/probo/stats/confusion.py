# SPDX-License-Identifier: Apache-2.0
"""Binary confusion matrix of an LLM judge against a deterministic check."""

from collections.abc import Iterable
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from probo.stats.rate import Proportion, render_optional

_Count = Annotated[int, Field(ge=0)]


def _proportion(successes: int, trials: int, level: float) -> Proportion | None:
    return None if trials == 0 else Proportion.from_counts(successes, trials, level=level)


class ConfusionMatrix(BaseModel):
    """Judge predictions against deterministic-check references for one binary question.

    The reference is the deterministic check, the prediction is the judge, and the positive
    class is "attack succeeded". A prediction of None is the judge answering "unknown"; such
    pairs are counted apart, split by their reference so both recall variants are computable:

    - tp: reference True, prediction True      - fp: reference False, prediction True
    - fn: reference True, prediction False     - tn: reference False, prediction False
    - unknown_positive: reference True, None   - unknown_negative: reference False, None

    Every proportion method returns a ``Proportion`` with a Wilson interval at ``level``, or
    None when its denominator is 0. Build one with ``from_pairs``.
    """

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    tp: _Count = 0
    """Reference positive, judge positive."""
    fp: _Count = 0
    """Reference negative, judge positive."""
    fn: _Count = 0
    """Reference positive, judge negative."""
    tn: _Count = 0
    """Reference negative, judge negative."""
    unknown_positive: _Count = 0
    """Reference positive, judge answered unknown."""
    unknown_negative: _Count = 0
    """Reference negative, judge answered unknown."""

    @classmethod
    def from_pairs(cls, pairs: Iterable[tuple[bool, bool | None]]) -> "ConfusionMatrix":
        """Count (reference, prediction) pairs; raises ``TypeError`` for a non-bool value."""
        counts = dict.fromkeys(cls.model_fields, 0)
        for reference, predicted in pairs:
            if reference is True:
                positive = True
            elif reference is False:
                positive = False
            else:
                raise TypeError(f"reference must be a bool, got {reference!r}")
            if predicted is None:
                key = "unknown_positive" if positive else "unknown_negative"
            elif predicted is True:
                key = "tp" if positive else "fp"
            elif predicted is False:
                key = "fn" if positive else "tn"
            else:
                raise TypeError(f"prediction must be a bool or None, got {predicted!r}")
            counts[key] += 1
        return cls.model_validate(counts)

    @property
    def unknown(self) -> int:
        """unknown_positive + unknown_negative: pairs where the judge answered unknown."""
        return self.unknown_positive + self.unknown_negative

    @property
    def positives(self) -> int:
        """tp + fn + unknown_positive: pairs whose reference is positive."""
        return self.tp + self.fn + self.unknown_positive

    @property
    def total(self) -> int:
        """Number of pairs: tp + fp + fn + tn + unknown."""
        return self.tp + self.fp + self.fn + self.tn + self.unknown

    def base_rate(self, level: float = 0.95) -> Proportion | None:
        """(tp + fn + unknown_positive) / total: share of reference positives over all pairs.

        Unknown predictions are included, since the reference is known for every pair.
        """
        return _proportion(self.positives, self.total, level)

    def precision(self, level: float = 0.95) -> Proportion | None:
        """tp / (tp + fp): share of judge positives that the check confirms; unknowns excluded."""
        return _proportion(self.tp, self.tp + self.fp, level)

    def recall(self, level: float = 0.95) -> Proportion | None:
        """tp / (tp + fn): share of decided reference positives the judge flags.

        Unknown predictions are excluded from the denominator, so a judge that abstains on
        hard cases can score high here; read it alongside ``recall_unknown_as_miss``.
        """
        return _proportion(self.tp, self.tp + self.fn, level)

    def recall_unknown_as_miss(self, level: float = 0.95) -> Proportion | None:
        """tp / (tp + fn + unknown_positive): recall with every unknown on a positive a miss.

        Abstaining cannot raise this value; it is <= ``recall`` whenever both exist.
        """
        return _proportion(self.tp, self.positives, level)

    def accuracy(self, level: float = 0.95) -> Proportion | None:
        """(tp + tn) / (tp + fp + fn + tn) over decided pairs. Not a headline metric.

        It misleads at low base rates: when few trials are reference positives, a judge that
        always answers "attack failed" scores accuracy 1 - base rate (0.95 at a 5% base rate)
        while its recall is 0. Report precision, recall and base rate instead.
        """
        return _proportion(self.tp + self.tn, self.tp + self.fp + self.fn + self.tn, level)

    def render(self, level: float = 0.95) -> str:
        """ASCII lines: the counts, base rate, precision and both recall variants (no accuracy)."""
        return "\n".join(
            [
                "judge vs deterministic check (positive = attack succeeded): "
                f"pairs={self.total} tp={self.tp} fp={self.fp} fn={self.fn} tn={self.tn} "
                f"unknown={self.unknown} (reference positive {self.unknown_positive}, "
                f"reference negative {self.unknown_negative})",
                "base rate: " + render_optional(self.base_rate(level)),
                "precision (unknown excluded): " + render_optional(self.precision(level)),
                "recall (unknown excluded): " + render_optional(self.recall(level)),
                "recall (unknown counted as miss): "
                + render_optional(self.recall_unknown_as_miss(level)),
            ]
        )
