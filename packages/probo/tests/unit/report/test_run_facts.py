# SPDX-License-Identifier: Apache-2.0
"""Run facts, incomplete runs, limits, corpus mismatch and the single meaning of delivered."""

from pathlib import Path

import pytest
from inspect_ai.log import EvalLog, EvalRevision, EvalSample
from inspect_ai.model import GenerateConfig

from probo.checks.result import RESULT_KEY, CheckResult
from probo.report import (
    CORPUS_WARNING,
    INCOMPLETE_WARNING,
    LIMIT_SENTENCE,
    LimitRow,
    RoleModel,
    TokenUsage,
    render_markdown,
    run_facts,
    summarise,
)
from probo.scenarios.helpdesk_exfil.keys import META_CORPUS_HASH, SCORER_RECORD_LEAKED
from probo.schema.outcome import Outcome

from ..outcomes.outcome_support import (
    corpus_args,
    failing_after_read_model,
    ordinary,
    raising_model,
    run_plan,
    watched_only,
)
from ..scenarios.helpdesk_support import MOCK_MODEL, run, scripted_agent


@pytest.fixture(scope="module")
def ordinary_log(tmp_path_factory: pytest.TempPathFactory) -> EvalLog:
    return run_plan(tmp_path_factory.mktemp("ordinary"), ordinary)


def test_roles_generate_config_and_token_usage(tmp_path: Path) -> None:
    """Each bound role's model and config, the eval config, and usage per model and role."""
    target = scripted_agent(ordinary)
    target.config = GenerateConfig(max_tokens=99)
    log = run(
        tmp_path / "logs",
        task_args=corpus_args(tmp_path),
        model_roles={"target": target},
        temperature=0.5,
    )
    facts = run_facts(log)
    assert facts.model_roles == {
        "target": (RoleModel(model=MOCK_MODEL, generate_config={"max_tokens": 99}),)
    }
    assert facts.generate_config == {"temperature": 0.5}
    assert facts.model_generate_config == {}
    usage = log.stats.model_usage[MOCK_MODEL]
    assert facts.token_usage == {MOCK_MODEL: TokenUsage.of(usage)}
    assert facts.token_usage[MOCK_MODEL].input_tokens == usage.input_tokens
    assert facts.token_usage[MOCK_MODEL].output_tokens == usage.output_tokens
    assert usage.input_tokens != usage.output_tokens
    assert facts.role_usage == {"target": TokenUsage.of(log.stats.role_usage["target"])}
    text = render_markdown(summarise(log))
    assert "| Model roles | target: mockllm/model (max_tokens=99) |" in text
    assert "| Generate config (eval) | temperature=0.5 |" in text
    assert "| Generate config (model) | defaults |" in text
    assert f"| role target | {usage.input_tokens} |" in text


def test_unbound_roles_and_default_config_are_not_missing(ordinary_log: EvalLog) -> None:
    """No role bound reads none and an all-default config reads defaults, not unrecorded."""
    text = render_markdown(summarise(ordinary_log))
    assert "| Model roles | none |" in text
    assert "| Generate config (eval) | defaults |" in text


def test_revision_is_reported(ordinary_log: EvalLog) -> None:
    """The git commit, marked dirty for a dirty tree."""
    revision = EvalRevision(type="git", origin="origin", commit="abc1234", dirty=True)
    log = ordinary_log.model_copy(
        update={"eval": ordinary_log.eval.model_copy(update={"revision": revision})}
    )
    assert run_facts(log).revision == "abc1234 (dirty)"
    assert "| Revision | abc1234 (dirty) |" in render_markdown(summarise(log))


def test_trials_not_run_make_the_run_incomplete(tmp_path: Path) -> None:
    """A run stopped by an error: the missing trials are counted and the report warns."""
    log = run(
        tmp_path / "logs",
        raising_model(),
        task_args=corpus_args(tmp_path),
        status="error",
        epochs=3,
        max_samples=1,
    )
    summary = summarise(log)
    assert summary.facts.expected_trials == 12
    assert summary.not_run is not None and summary.not_run == 12 - summary.trials > 0
    assert summary.incomplete
    assert summary.warnings == (INCOMPLETE_WARNING,)
    text = render_markdown(summary)
    assert text.splitlines()[2] == f"**{INCOMPLETE_WARNING}**"
    assert f"| not run | {summary.not_run} |" in text


def test_complete_run_has_no_warning(ordinary_log: EvalLog) -> None:
    """All expected trials present and status success: no warning, not run 0."""
    summary = summarise(ordinary_log)
    assert (summary.not_run, summary.incomplete, summary.warnings) == (0, False, ())
    assert "| not run | 0 |" in render_markdown(summary)


def test_limits_are_shown_per_outcome(tmp_path: Path) -> None:
    """Resisted trials cut off by a limit are counted by type and listed."""
    args = {**corpus_args(tmp_path), "message_limit": 5}
    summary = summarise(run(tmp_path / "logs", scripted_agent(ordinary), task_args=args))
    assert summary.limits == (
        LimitRow(
            kind="template",
            outcome=Outcome.ATTACK_FAILED_TARGET_RESISTED,
            trials=2,
            limits={"message": 2},
        ),
        LimitRow(kind="control", outcome=None, trials=2, limits={"message": 2}),
    )
    text = render_markdown(summary)
    assert LIMIT_SENTENCE in text
    assert "| template | attack_failed_target_resisted | 2 | 2 | message=2 |" in text
    assert "Resisted trials that hit a limit: 2." in text
    assert "| reply-order-status/copy-note | 1 | message |" in text


def test_outage_under_a_time_limit_is_not_a_resisted_rate(tmp_path: Path) -> None:
    """Every call failing until the time limit: provider errors, no per-attempt rate."""
    log = run(
        tmp_path / "logs", failing_after_read_model(), task_args=corpus_args(tmp_path), time_limit=3
    )
    summary = summarise(log)
    assert summary.attack.counts[Outcome.PROVIDER_ERROR] == 2
    assert summary.attack.per_attempt is None
    assert "| template | provider_error | 2 | 2 | time=2 |" in render_markdown(summary)


def with_samples(log: EvalLog, samples: list[EvalSample]) -> EvalLog:
    return log.model_copy(update={"samples": samples})


def test_corpus_mismatch_is_flagged(ordinary_log: EvalLog) -> None:
    """A sample recording another corpus hash is shown and warned about."""
    samples = list(ordinary_log.samples or [])
    first = samples[0]
    samples[0] = first.model_copy(update={"metadata": {**first.metadata, META_CORPUS_HASH: "x"}})
    summary = summarise(with_samples(ordinary_log, samples))
    facts = summary.facts
    assert facts.corpus_mismatch
    assert "x" in facts.sample_corpus_hashes and len(facts.sample_corpus_hashes) == 2
    assert facts.sample_corpus_versions == ("2026-11",)
    assert CORPUS_WARNING in summary.warnings
    assert not summarise(ordinary_log).facts.corpus_mismatch


def test_delivered_means_note_delivered_everywhere(ordinary_log: EvalLog) -> None:
    """A grader-error trial whose note was delivered counts as delivered in every section."""
    samples = list(ordinary_log.samples or [])
    index = next(i for i, s in enumerate(samples) if str(s.id) == "reply-order-status/copy-note")
    sample = samples[index]
    scores = dict(sample.scores or {})
    scores[SCORER_RECORD_LEAKED] = scores[SCORER_RECORD_LEAKED].model_copy(
        update={"metadata": {RESULT_KEY: "bogus"}}
    )
    samples[index] = sample.model_copy(update={"scores": scores})
    summary = summarise(with_samples(ordinary_log, samples))
    label = next(lb for lb in summary.labels if str(lb.sample_id) == str(sample.id))
    assert (label.outcome, label.note_delivered) == (Outcome.GRADER_ERROR, CheckResult.TRUE)
    assert summary.delivered == summary.delivery.true == 2
    assert summary.attempted.trials == summary.completed.trials == 2
    assert summary.completed.missing == 1
    assert summary.attack.per_attempt is not None and summary.attack.per_attempt.trials == 1


def test_control_attempted_rate_reads_the_watch_check(tmp_path: Path) -> None:
    """Control attempted counts sent_to_watched_address, completed counts record_leaked."""
    control = summarise(run_plan(tmp_path, watched_only)).control
    assert control.sent_to_watched_address.true == 2
    assert control.record_leaked.true == 0
