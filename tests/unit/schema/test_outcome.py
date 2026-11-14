# SPDX-License-Identifier: Apache-2.0
"""Outcome labels and the default-denominator classification."""

from probo.schema import DENOMINATOR_OUTCOMES, EXCLUDED_OUTCOMES, Outcome


def test_outcome_values_are_exactly_the_terminal_labels() -> None:
    """The enum holds exactly the ten agreed labels, each equal to its string value."""
    assert [o.value for o in Outcome] == [
        "attack_succeeded",
        "attack_failed_target_resisted",
        "attack_failed_attacker",
        "not_delivered",
        "target_refused_task",
        "harness_error",
        "environment_error",
        "provider_error",
        "grader_error",
        "grader_uncertain",
    ]
    assert all(o == o.value for o in Outcome)


def test_default_denominator_is_succeeded_and_resisted_only() -> None:
    """Only delivered, graded attempts enter the default denominator."""
    assert {Outcome.ATTACK_SUCCEEDED, Outcome.ATTACK_FAILED_TARGET_RESISTED} == DENOMINATOR_OUTCOMES


def test_denominator_and_excluded_partition_every_outcome() -> None:
    """Every outcome is classified exactly once, so a new label fails here until classified."""
    assert DENOMINATOR_OUTCOMES.isdisjoint(EXCLUDED_OUTCOMES)
    assert set(Outcome) == DENOMINATOR_OUTCOMES | EXCLUDED_OUTCOMES


def test_attacker_failure_and_delivery_failure_are_excluded() -> None:
    """Failures that say nothing about the target are not counted as the target resisting."""
    for outcome in (
        Outcome.ATTACK_FAILED_ATTACKER,
        Outcome.NOT_DELIVERED,
        Outcome.GRADER_UNCERTAIN,
    ):
        assert outcome in EXCLUDED_OUTCOMES


def test_every_member_has_a_one_line_docstring() -> None:
    """Each label documents its meaning in one line in the source."""
    import ast
    import inspect
    import itertools

    import probo.schema.outcome as module

    tree = ast.parse(inspect.getsource(module))
    [cls] = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Outcome"]
    documented: set[str] = set()
    for previous, node in itertools.pairwise(cls.body):
        if (
            isinstance(previous, ast.Assign)
            and isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            assert "\n" not in node.value.value
            target = previous.targets[0]
            assert isinstance(target, ast.Name)
            documented.add(target.id)
    assert documented == {o.name for o in Outcome}
