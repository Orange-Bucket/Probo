# SPDX-License-Identifier: Apache-2.0
"""Judge-versus-check confusion matrix: precision, recall, base rate and unknown handling."""

from collections.abc import Callable, Iterable
from typing import cast

import pytest
from pydantic import ValidationError

from probo.stats import ConfusionMatrix, Proportion

Pair = tuple[bool, bool | None]


def pairs(
    tp: int = 0,
    fp: int = 0,
    fn: int = 0,
    tn: int = 0,
    unknown_positive: int = 0,
    unknown_negative: int = 0,
) -> list[Pair]:
    kinds: list[tuple[Pair, int]] = [
        ((True, True), tp),
        ((False, True), fp),
        ((True, False), fn),
        ((False, False), tn),
        ((True, None), unknown_positive),
        ((False, None), unknown_negative),
    ]
    return [pair for pair, count in kinds for _ in range(count)]


def counts(proportion: Proportion | None) -> tuple[int, int]:
    assert proportion is not None
    return proportion.successes, proportion.trials


def test_worked_example() -> None:
    """tp=8 fp=2 fn=4 tn=86 unknown=3+1: precision 8/10, recall 8/12, base rate 15/104."""
    matrix = ConfusionMatrix.from_pairs(pairs(8, 2, 4, 86, 3, 1))
    assert (matrix.tp, matrix.fp, matrix.fn, matrix.tn) == (8, 2, 4, 86)
    assert (matrix.unknown_positive, matrix.unknown_negative, matrix.unknown) == (3, 1, 4)
    assert matrix.total == 104
    assert counts(matrix.precision()) == (8, 10)
    assert counts(matrix.recall()) == (8, 12)
    assert counts(matrix.recall_unknown_as_miss()) == (8, 15)
    assert counts(matrix.base_rate()) == (15, 104)
    precision = matrix.precision()
    recall = matrix.recall()
    assert precision is not None
    assert recall is not None
    assert precision.estimate == pytest.approx(0.8)
    assert recall.estimate == pytest.approx(2 / 3)
    assert precision == Proportion.from_counts(8, 10)


def test_pair_order_does_not_matter() -> None:
    """The matrix depends only on the counts of each pair kind."""
    forward = pairs(3, 1, 2, 5, 1, 1)
    assert ConfusionMatrix.from_pairs(forward) == ConfusionMatrix.from_pairs(reversed(forward))


def test_level_reaches_every_interval() -> None:
    """The level argument sets the Wilson level of each proportion."""
    matrix = ConfusionMatrix.from_pairs(pairs(8, 2, 4, 86))
    for method in (
        matrix.precision,
        matrix.recall,
        matrix.recall_unknown_as_miss,
        matrix.base_rate,
    ):
        proportion = method(0.9)
        assert proportion is not None
        assert proportion.level == 0.9


def test_unknowns_excluded_from_recall_but_counted_as_misses_in_strict_recall() -> None:
    """A judge that abstains on every hard positive keeps recall 1.0 but not the strict one."""
    matrix = ConfusionMatrix.from_pairs(pairs(tp=2, tn=10, unknown_positive=8))
    assert counts(matrix.recall()) == (2, 2)
    assert counts(matrix.recall_unknown_as_miss()) == (2, 10)
    assert counts(matrix.precision()) == (2, 2)
    assert matrix.unknown == 8


def test_unknown_on_negatives_affects_neither_precision_nor_recall() -> None:
    """Unknowns on reference negatives are counted but leave precision and recall alone."""
    base = ConfusionMatrix.from_pairs(pairs(5, 1, 2, 10))
    with_unknown = ConfusionMatrix.from_pairs(pairs(5, 1, 2, 10, unknown_negative=7))
    assert with_unknown.precision() == base.precision()
    assert with_unknown.recall() == base.recall()
    assert with_unknown.recall_unknown_as_miss() == base.recall_unknown_as_miss()
    assert with_unknown.unknown == 7


def test_strict_recall_never_exceeds_recall() -> None:
    """recall_unknown_as_miss <= recall whenever both exist."""
    for tp in range(4):
        for fn in range(4):
            for unknown in range(4):
                matrix = ConfusionMatrix.from_pairs(pairs(tp=tp, fn=fn, unknown_positive=unknown))
                recall = matrix.recall()
                strict = matrix.recall_unknown_as_miss()
                if recall is not None and strict is not None:
                    assert strict.estimate <= recall.estimate


def test_zero_denominators_give_none() -> None:
    """No judge positives: precision None. No reference positives: both recalls None."""
    only_negatives = ConfusionMatrix.from_pairs(pairs(tn=5))
    assert only_negatives.precision() is None
    assert only_negatives.recall() is None
    assert only_negatives.recall_unknown_as_miss() is None
    assert counts(only_negatives.base_rate()) == (0, 5)

    only_unknown_positives = ConfusionMatrix.from_pairs(pairs(unknown_positive=3))
    assert only_unknown_positives.recall() is None
    assert counts(only_unknown_positives.recall_unknown_as_miss()) == (0, 3)
    assert only_unknown_positives.accuracy() is None

    empty = ConfusionMatrix.from_pairs([])
    assert empty.total == 0
    assert empty.base_rate() is None
    assert empty.precision() is None
    assert "absent (denominator is 0)" in empty.render()


def test_low_base_rate_gives_high_accuracy_with_zero_recall() -> None:
    """5% positives and a judge that always says "failed": accuracy 0.95, recall 0.

    This is why Probo reports precision, recall and base rate rather than accuracy.
    """
    matrix = ConfusionMatrix.from_pairs(pairs(fn=5, tn=95))
    accuracy = matrix.accuracy()
    recall = matrix.recall()
    assert accuracy is not None
    assert recall is not None
    assert accuracy.estimate == pytest.approx(0.95)
    assert recall.estimate == 0.0
    assert recall.interval.lower == 0.0
    assert matrix.precision() is None
    base_rate = matrix.base_rate()
    assert base_rate is not None
    assert base_rate.estimate == pytest.approx(0.05)
    assert "accuracy" not in matrix.render()


def test_render_lists_counts_base_rate_precision_and_both_recalls() -> None:
    """Five ASCII lines with every count and each proportion labelled."""
    text = ConfusionMatrix.from_pairs(pairs(8, 2, 4, 86, 3, 1)).render()
    assert text.isascii()
    header, base_rate, precision, recall, strict = text.splitlines()
    assert "pairs=104 tp=8 fp=2 fn=4 tn=86 unknown=4" in header
    assert base_rate.startswith("base rate: 0.144 ")
    assert precision == "precision (unknown excluded): 0.800 [0.490, 0.943] (n=10, 95% Wilson)"
    assert recall.startswith("recall (unknown excluded): 0.667 ")
    assert strict.startswith("recall (unknown counted as miss): 0.533 ")


def test_rejects_non_bool_reference_or_prediction() -> None:
    """References must be bool; predictions bool or None. Ints and strings are refused."""
    untyped = cast(
        Callable[[Iterable[tuple[object, object]]], ConfusionMatrix], ConfusionMatrix.from_pairs
    )
    for bad in [(1, True), (None, True), (True, 1), (True, "unknown"), (False, 0)]:
        with pytest.raises(TypeError):
            untyped([bad])


def test_rejects_negative_or_non_int_counts() -> None:
    """Direct construction validates the counts strictly."""
    with pytest.raises(ValidationError):
        ConfusionMatrix(tp=-1)
    with pytest.raises(ValidationError):
        ConfusionMatrix.model_validate({"tp": 1.0})
    with pytest.raises(ValidationError):
        ConfusionMatrix.model_validate({"accuracy": 1})


def test_matrix_is_frozen_and_round_trips() -> None:
    """A matrix is immutable and loads back equal from JSON."""
    matrix = ConfusionMatrix.from_pairs(pairs(1, 2, 3, 4, 5, 6))
    with pytest.raises(ValidationError):
        matrix.__setattr__("tp", 0)
    assert ConfusionMatrix.model_validate_json(matrix.model_dump_json()) == matrix
