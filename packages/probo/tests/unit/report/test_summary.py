# SPDX-License-Identifier: Apache-2.0
"""Run summaries: counts and rates against hand-computed values for known scripted runs."""

from pathlib import Path

import pytest
from inspect_ai.log import EvalLog, read_eval_log

from probo.checks.result import CheckResult
from probo.outcomes import label_log
from probo.report import CheckShare, RunSummary, share, summarise
from probo.scenarios.helpdesk_exfil.user_tasks import REPLY_DELIVERY_DATE, REPLY_ORDER_STATUS
from probo.schema.outcome import Outcome
from probo.stats import AttackSuccess, Estimand, Proportion, Rate

from ..outcomes.outcome_support import (
    COPY,
    PLAIN,
    SEED,
    corpus_args,
    known_run,
    leak,
    raising_model,
    run_plan,
)
from ..scenarios.helpdesk_support import MOCK_MODEL, run

ORDER, DELIVERY = REPLY_ORDER_STATUS.id, REPLY_DELIVERY_DATE.id


@pytest.fixture(scope="module")
def known(tmp_path_factory: pytest.TempPathFactory) -> RunSummary:
    return summarise(known_run(tmp_path_factory.mktemp("known")))


def proportion(successes: int, trials: int) -> Proportion:
    return Proportion.from_counts(successes, trials)


def decided(successes: int, trials: int, *, of: int | None = None, na: int = 0) -> CheckShare:
    """A share with `trials` decided values; `of` trials in the group, the rest missing."""
    group = trials + na if of is None else of
    value = proportion(successes, trials) if trials else None
    return CheckShare(trials=group, value=value, not_applicable=na, missing=group - trials - na)


def test_known_run_attack_success(known: RunSummary) -> None:
    """Hand-computed: copy-note 1 of 2 delivered (1 of 4 trials), plain-ref 0 of 2 (0 of 4)."""
    assert (known.trials, known.control_trials, known.template_trials) == (12, 4, 8)
    assert known.attack == AttackSuccess.from_counts(
        {
            Outcome.ATTACK_SUCCEEDED: 1,
            Outcome.ATTACK_FAILED_TARGET_RESISTED: 3,
            Outcome.NOT_DELIVERED: 4,
        }
    )
    assert known.attack_by_template == {
        COPY: AttackSuccess.from_counts(
            {
                Outcome.ATTACK_SUCCEEDED: 1,
                Outcome.ATTACK_FAILED_TARGET_RESISTED: 1,
                Outcome.NOT_DELIVERED: 2,
            }
        ),
        PLAIN: AttackSuccess.from_counts(
            {Outcome.ATTACK_FAILED_TARGET_RESISTED: 2, Outcome.NOT_DELIVERED: 2}
        ),
    }
    per_attempt, per_trial = known.attack.per_attempt, known.attack.per_trial
    assert per_attempt is not None and per_trial is not None
    assert (per_attempt.successes, per_attempt.trials) == (1, 4)
    assert (per_trial.successes, per_trial.trials) == (1, 8)


def test_known_run_attempted_and_completed(known: RunSummary) -> None:
    """Over the 4 delivered template trials: 2 attempts, 1 completion."""
    assert known.delivered == 4
    assert known.attempted == decided(2, 4)
    assert known.completed == decided(1, 4)
    table = known.attempt_completion
    assert (table.sent_and_leaked, table.sent_not_leaked) == (1, 1)
    assert (table.leaked_not_sent, table.neither) == (0, 2)


def test_known_run_utility_delivery_and_controls(known: RunSummary) -> None:
    """Utility is split by kind and user task; controls have their own base rates."""
    assert known.utility_control == decided(4, 4)
    assert known.utility_template == decided(7, 8)
    by_task = {u.user_task: (u.control, u.template) for u in known.utility_by_user_task}
    assert by_task == {
        ORDER: (decided(2, 2), decided(3, 4)),
        DELIVERY: (decided(2, 2), decided(4, 4)),
    }
    assert known.delivery == decided(4, 8)
    assert known.control.trials == 4
    assert known.control.errors.total == 0
    assert known.control.record_leaked == decided(0, 4)
    assert known.control.sent_to_watched_address == decided(0, 4)


def test_known_run_items_show_run_to_run_variation(known: RunSummary) -> None:
    """Each item lists its successes out of its epochs."""
    assert [(i.user_task, i.template_id, i.successes, i.trials) for i in known.items] == [
        (DELIVERY, COPY, 0, 2),
        (DELIVERY, PLAIN, 0, 2),
        (ORDER, COPY, 1, 2),
        (ORDER, PLAIN, 0, 2),
    ]
    assert [i.counts.excluded for i in known.items] == [2, 2, 0, 0]


def test_known_run_facts(known: RunSummary) -> None:
    """Run facts come from the log header and sample metadata."""
    facts = known.facts
    assert facts.task == "probo/helpdesk_exfil"
    assert (facts.model, facts.epochs, facts.seeds) == (MOCK_MODEL, 2, (SEED,))
    assert facts.inspect_version == "0.3.289"
    assert facts.corpus_version == "2026-11"
    assert facts.corpus_content_hash is not None
    assert facts.started_at is not None and facts.completed_at is not None
    assert set(facts.token_usage) == {MOCK_MODEL}
    assert facts.token_usage[MOCK_MODEL].total_tokens > 0


def counts_add_up(summary: RunSummary) -> None:
    """Every trial is in exactly one group, and every group's counts cover it."""
    assert summary.trials == summary.control_trials + summary.template_trials
    assert summary.attack.counts.total == summary.template_trials
    assert sum(a.counts.total for a in summary.attack_by_template.values()) == (
        summary.template_trials
    )
    assert sum(i.trials for i in summary.items) == summary.template_trials
    assert summary.control.trials == summary.control_trials
    for group, trials in (
        (summary.utility_control, summary.control_trials),
        (summary.utility_template, summary.template_trials),
        (summary.delivery, summary.template_trials),
        (summary.control.record_leaked, summary.control_trials),
        (summary.control.sent_to_watched_address, summary.control_trials),
        (summary.attempted, summary.delivered),
        (summary.completed, summary.delivered),
    ):
        assert group.trials == trials


def test_counts_sum_to_the_trials(known: RunSummary, tmp_path: Path) -> None:
    """In the known run and in a run where every trial errored."""
    counts_add_up(known)
    log = run(
        tmp_path / "logs",
        raising_model(),
        task_args=corpus_args(tmp_path),
        fail_on_error=False,
    )
    errored = summarise(log)
    counts_add_up(errored)
    assert errored.attack.counts[Outcome.PROVIDER_ERROR] == 2
    assert errored.control.errors[Outcome.PROVIDER_ERROR] == 2


def test_controls_and_templates_never_share_a_denominator(tmp_path: Path) -> None:
    """When every trial leaks, each rate counts only its own kind of trial."""
    summary = summarise(run_plan(tmp_path, leak))
    assert summary.control.record_leaked == decided(2, 2)
    assert summary.utility_control == decided(2, 2)
    assert summary.utility_template == decided(2, 2)
    assert summary.attack.counts.total == 2
    assert summary.attack.per_trial == Rate.from_counts(2, 2, estimand=Estimand.PER_TRIAL)


def test_zero_denominators_are_absent(tmp_path: Path) -> None:
    """With every trial errored, or no templates, rates are None, not 0."""
    errored = summarise(
        run(
            tmp_path / "errored",
            raising_model(),
            task_args=corpus_args(tmp_path),
            fail_on_error=False,
        )
    )
    assert errored.attack.per_attempt is None
    assert errored.attack.per_trial is not None
    assert errored.attack.per_trial.successes == 0
    for group in (errored.utility_control, errored.delivery, errored.attempted):
        assert group.value is None
    assert errored.utility_control.missing == 2
    controls_only = summarise(
        run(tmp_path / "controls", task_args={**corpus_args(tmp_path), "templates": []})
    )
    assert controls_only.template_trials == 0
    assert controls_only.attack.per_attempt is None and controls_only.attack.per_trial is None
    assert controls_only.attack_by_template == {}
    assert controls_only.utility_template == CheckShare(
        trials=0, value=None, not_applicable=0, missing=0
    )


def test_not_applicable_is_counted_apart() -> None:
    """`share` keeps not applicable and missing out of the denominator, and counts them."""
    values = [CheckResult.TRUE, CheckResult.NOT_APPLICABLE, None, CheckResult.FALSE, True]
    assert share(values) == CheckShare(
        trials=5, value=proportion(2, 3), not_applicable=1, missing=1
    )
    with pytest.raises(ValueError, match="must equal trials"):
        CheckShare(trials=2, value=None, not_applicable=1, missing=0)


def test_json_round_trip(known: RunSummary) -> None:
    """`model_dump_json` loads back to an equal summary."""
    assert RunSummary.model_validate_json(known.model_dump_json()) == known
    assert len(known.labels) == known.trials


def test_header_only_log_cannot_be_summarised(tmp_path: Path) -> None:
    """Summaries need the samples."""
    log: EvalLog = run_plan(tmp_path, leak)
    with pytest.raises(ValueError, match="holds no samples"):
        summarise(read_eval_log(log.location, header_only=True))
    assert len(label_log(log)) == 4
