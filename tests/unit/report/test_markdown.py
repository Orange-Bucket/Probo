# SPDX-License-Identifier: Apache-2.0
"""Markdown report: every rate with its n and interval, the fixed sentences, ASCII only."""

from pathlib import Path

import pytest

from probo.report import (
    EVIDENCE_SENTENCE,
    GRADER_SENTENCE,
    INDEPENDENCE_SENTENCE,
    TERMS,
    CheckShare,
    RunSummary,
    render_markdown,
    summarise,
)
from probo.stats.rate import render_optional

from ..outcomes.outcome_support import corpus_args, known_run, raising_model
from ..scenarios.helpdesk_support import run


@pytest.fixture(scope="module")
def known(tmp_path_factory: pytest.TempPathFactory) -> RunSummary:
    return summarise(known_run(tmp_path_factory.mktemp("known")))


def shares(summary: RunSummary) -> list[CheckShare]:
    found = [
        summary.attempted,
        summary.completed,
        summary.utility_control,
        summary.utility_template,
        summary.control.record_leaked,
        summary.control.sent_to_watched_address,
        summary.delivery,
    ]
    for task in summary.utility_by_user_task:
        found.extend([task.control, task.template])
    return found


def test_every_rate_is_printed_with_n_interval_and_estimand(known: RunSummary) -> None:
    """Each rate appears exactly as its stats `render()` prints it."""
    text = render_markdown(known)
    for attack in (known.attack, *known.attack_by_template.values()):
        for rate in (attack.per_attempt, attack.per_trial):
            assert rate is not None
            rendered = rate.render()
            assert f"n={rate.trials}" in rendered and f"{rate.label}" in rendered
            assert rendered in text
    for found in shares(known):
        assert found.value is not None
        assert f"| {found.value.render()} |" in text
    assert "0.250 [" in text and "(n=4, per-attempt, 95% Wilson)" in text
    assert "(n=8, per-trial, 95% Wilson)" in text


def test_fixed_sentences_and_ascii(known: RunSummary) -> None:
    """The two fixed sentences are present and the report is ASCII."""
    text = render_markdown(known)
    assert EVIDENCE_SENTENCE in text
    assert INDEPENDENCE_SENTENCE in text
    assert text.isascii()


def test_items_and_excluded_trials_are_listed(known: RunSummary) -> None:
    """Items print successes out of epochs; every excluded trial is listed with evidence."""
    text = render_markdown(known)
    assert "| reply-order-status | copy-note | 1 of 2 | 2 | 0 |" in text
    assert "| reply-delivery-date | plain-ref | 0 of 2 | 0 | 2 |" in text
    assert "error label: 4." in text
    assert text.count("| not_delivered | note_delivered=false |") == 4


def test_absent_rates_are_printed_as_absent(tmp_path: Path) -> None:
    """Zero denominators print as absent, never as 0."""
    log = run(
        tmp_path / "logs", raising_model(), task_args=corpus_args(tmp_path), fail_on_error=False
    )
    summary = summarise(log)
    text = render_markdown(summary)
    assert summary.attack.per_attempt is None
    assert render_optional(None) == "absent (denominator is 0)"
    assert text.count("absent (denominator is 0)") >= 8
    assert "| provider_error | excluded | 2 | 2 |" in text
    assert "With an error label: 2 (provider_error=2)." in text
    for task in ("reply-order-status", "reply-delivery-date"):
        assert f"| {task}/none | 1 | control | provider_error |" in text
        assert f"| {task}/copy-note | 1 | template | provider_error |" in text
    assert "error type: ProviderDown" in text


def test_terms_and_label_coverage_are_stated(known: RunSummary) -> None:
    """The report defines its terms and says what the error labels cover."""
    text = render_markdown(known)
    assert TERMS in text
    assert GRADER_SENTENCE in text
    assert "pooled rows combine templates and user tasks" in INDEPENDENCE_SENTENCE
    assert "| attempted, delivered template trials | 4 |" in text
    assert "| delivered, template trials | 8 |" in text
