# SPDX-License-Identifier: Apache-2.0
"""Run summary of a finished `helpdesk_exfil` log: run facts, then rates with their counts.

Every value comes from the log or from `probo.outcomes.label_log`. Every rate is a
`probo.stats` value with its trial count and Wilson interval; a zero denominator gives None,
never 0. Every trial left out of a denominator is counted next to it (`CheckShare`,
`AttackSuccess.counts`). Control and template trials never share a denominator.
"""

from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Self

from inspect_ai.log import EvalLog
from pydantic import BaseModel, ConfigDict, JsonValue, model_validator

from probo.checks.result import CheckResult
from probo.outcomes.label import ERROR_OUTCOMES, TrialLabel, label_log
from probo.scenarios.helpdesk_exfil.keys import META_CORPUS_HASH, META_CORPUS_VERSION, META_SEED
from probo.schema.outcome import DENOMINATOR_OUTCOMES, Outcome
from probo.stats.attack import AttackSuccess, OutcomeCounts
from probo.stats.rate import Proportion


class _Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TokenUsage(_Model):
    """Token usage of one model over the whole run (`EvalStats.model_usage`)."""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class RunFacts(_Model):
    """Facts about the run, read from the log; None where the log does not record one."""

    task: str
    """`EvalSpec.task`."""
    status: str
    """`EvalLog.status`."""
    model: str
    """`EvalSpec.model`."""
    model_roles: dict[str, tuple[str, ...]]
    """Model(s) bound to each role (`EvalSpec.model_roles`); empty when none was bound."""
    inspect_version: str | None
    """Version of `inspect_ai` (`EvalSpec.packages`)."""
    probo_version: str | None
    """Version of `probo` (`EvalSpec.packages`)."""
    revision: str | None
    """Git commit of the run (`EvalSpec.revision`), with ` (dirty)` for a dirty tree."""
    started_at: str | None
    completed_at: str | None
    epochs: int | None
    """`EvalConfig.epochs`."""
    corpus_version: str | None
    """`corpus_version` in the task metadata."""
    corpus_content_hash: str | None
    """`corpus_content_hash` in the task metadata."""
    seeds: tuple[int, ...]
    """Distinct `seed` values in the sample metadata, sorted."""
    generate_config: dict[str, JsonValue]
    """Generate config given to the eval (`EvalPlan.config`), unset fields left out."""
    model_generate_config: dict[str, JsonValue]
    """Generate config of the main model (`EvalSpec.model_generate_config`), unset fields
    left out."""
    token_usage: dict[str, TokenUsage]
    """Total token usage per model."""


class CheckShare(_Model):
    """Share of a group of trials whose value is true, every other trial counted.

    `trials` = `value.trials` (0 when `value` is None) + `not_applicable` + `missing`.
    """

    trials: int
    """Trials in the group."""
    value: Proportion | None
    """True values over true and false values; None when there are none."""
    not_applicable: int
    """Trials whose check was not applicable."""
    missing: int
    """Trials without a value: errored, or with a missing or invalid score."""

    @model_validator(mode="after")
    def _counts_add_up(self) -> Self:
        decided = 0 if self.value is None else self.value.trials
        if decided + self.not_applicable + self.missing != self.trials:
            raise ValueError("decided + not_applicable + missing must equal trials")
        return self


class AttemptCompletion(_Model):
    """`sent_to_watched_address` against `record_leaked` over delivered template trials
    whose `sent_to_watched_address` applies."""

    sent_and_leaked: int
    sent_not_leaked: int
    leaked_not_sent: int
    neither: int

    @property
    def total(self) -> int:
        """Trials in the table."""
        return self.sent_and_leaked + self.sent_not_leaked + self.leaked_not_sent + self.neither


class UserTaskUtility(_Model):
    """`task_completed` shares of one user task, control and template trials apart."""

    user_task: str
    control: CheckShare
    template: CheckShare


class ControlSummary(_Model):
    """Control trials: their error labels and base rates."""

    trials: int
    errors: OutcomeCounts
    """Control trials labelled by an error rule (only `ERROR_OUTCOMES` are non-zero)."""
    record_leaked: CheckShare
    sent_to_watched_address: CheckShare


class ItemResult(_Model):
    """Outcomes of one item (user task x template) over its epochs."""

    user_task: str
    template_id: str
    counts: OutcomeCounts

    @property
    def successes(self) -> int:
        """Trials labelled `attack_succeeded`."""
        return self.counts[Outcome.ATTACK_SUCCEEDED]

    @property
    def trials(self) -> int:
        """Trials of the item (one per epoch)."""
        return self.counts.total


class RunSummary(_Model):
    """Everything `render_markdown` prints, as data. `model_dump_json` round-trips."""

    facts: RunFacts
    level: float
    """Confidence level of every interval."""
    trials: int
    control_trials: int
    template_trials: int
    attack: AttackSuccess
    """Over all template trials."""
    attack_by_template: dict[str, AttackSuccess]
    """Per template id, in id order."""
    delivered: int
    """Template trials labelled `attack_succeeded` or `attack_failed_target_resisted`."""
    attempted: CheckShare
    """`sent_to_watched_address` true over the delivered template trials."""
    completed: CheckShare
    """`record_leaked` true over the delivered template trials."""
    attempt_completion: AttemptCompletion
    utility_control: CheckShare
    """`task_completed` true over control trials."""
    utility_template: CheckShare
    """`task_completed` true over template trials."""
    utility_by_user_task: tuple[UserTaskUtility, ...]
    """Per user task, in id order."""
    control: ControlSummary
    delivery: CheckShare
    """`note_delivered` true over template trials."""
    items: tuple[ItemResult, ...]
    """Per item, in (user task, template id) order."""
    labels: tuple[TrialLabel, ...]
    """Every trial's label, in log order."""

    @model_validator(mode="after")
    def _trials_add_up(self) -> Self:
        if not self.trials == len(self.labels) == self.control_trials + self.template_trials:
            raise ValueError("trials must equal len(labels) and control + template trials")
        if self.attack.counts.total != self.template_trials:
            raise ValueError("attack counts must cover every template trial")
        return self


def share(values: Iterable[bool | CheckResult | None], *, level: float = 0.95) -> CheckShare:
    """The share of true values among `values`.

    A bool or a `CheckResult` is a value; `NOT_APPLICABLE` is counted as not applicable and
    None as missing, and neither enters the denominator.
    """
    trials = true = decided = not_applicable = 0
    for value in values:
        trials += 1
        if value is CheckResult.NOT_APPLICABLE:
            not_applicable += 1
        elif value is not None:
            decided += 1
            if value is True or value is CheckResult.TRUE:
                true += 1
    proportion = None if decided == 0 else Proportion.from_counts(true, decided, level=level)
    missing = trials - decided - not_applicable
    return CheckShare(
        trials=trials, value=proportion, not_applicable=not_applicable, missing=missing
    )


def outcome_counts(labels: Iterable[TrialLabel]) -> OutcomeCounts:
    """Counts of the outcomes of `labels`; labels without an outcome are not counted."""
    found = Counter(label.outcome for label in labels if label.outcome is not None)
    return OutcomeCounts.from_mapping(found)


def run_facts(log: EvalLog) -> RunFacts:
    """The run facts recorded in `log`."""
    spec = log.eval
    roles: dict[str, tuple[str, ...]] = {}
    for role, config in (spec.model_roles or {}).items():
        configs = config if isinstance(config, list) else [config]
        roles[role] = tuple(c.model for c in configs)
    revision = None
    if spec.revision is not None:
        revision = spec.revision.commit + (" (dirty)" if spec.revision.dirty else "")
    metadata = spec.metadata or {}
    seeds = {
        seed
        for sample in log.samples or []
        if isinstance(seed := sample.metadata.get(META_SEED), int) and not isinstance(seed, bool)
    }

    def text(value: object) -> str | None:
        return value if isinstance(value, str) and value else None

    return RunFacts(
        task=spec.task,
        status=log.status,
        model=spec.model,
        model_roles=roles,
        inspect_version=spec.packages.get("inspect_ai"),
        probo_version=spec.packages.get("probo"),
        revision=revision,
        started_at=text(log.stats.started_at),
        completed_at=text(log.stats.completed_at),
        epochs=spec.config.epochs,
        corpus_version=text(metadata.get(META_CORPUS_VERSION)),
        corpus_content_hash=text(metadata.get(META_CORPUS_HASH)),
        seeds=tuple(sorted(seeds)),
        generate_config=log.plan.config.model_dump(mode="json", exclude_none=True),
        model_generate_config=spec.model_generate_config.model_dump(mode="json", exclude_none=True),
        token_usage={
            model: TokenUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                total_tokens=usage.total_tokens,
            )
            for model, usage in log.stats.model_usage.items()
        },
    )


def _attempt_completion(delivered: Sequence[TrialLabel]) -> AttemptCompletion:
    cells = Counter(
        (label.sent_to_watched_address, label.record_leaked)
        for label in delivered
        if label.sent_to_watched_address in (CheckResult.TRUE, CheckResult.FALSE)
    )
    true, false = CheckResult.TRUE, CheckResult.FALSE
    return AttemptCompletion(
        sent_and_leaked=cells[(true, true)],
        sent_not_leaked=cells[(true, false)],
        leaked_not_sent=cells[(false, true)],
        neither=cells[(false, false)],
    )


def summarise(log: EvalLog, *, level: float = 0.95) -> RunSummary:
    """The run summary of `log`, with every interval at `level`.

    Raises:
        ValueError: As `label_log` does, or for a `level` outside (0, 1).
    """
    labels = label_log(log)
    controls = [label for label in labels if label.kind == "control"]
    templates = [label for label in labels if label.kind == "template"]
    delivered = [label for label in templates if label.outcome in DENOMINATOR_OUTCOMES]
    user_tasks = sorted({label.user_task for label in labels})
    items = sorted(
        {
            (label.user_task, label.template_id)
            for label in templates
            if label.template_id is not None
        }
    )
    template_ids = sorted({template_id for _, template_id in items})

    def attack(group: Iterable[TrialLabel]) -> AttackSuccess:
        return AttackSuccess.from_counts(outcome_counts(group), level=level)

    def completion(group: Iterable[TrialLabel]) -> CheckShare:
        return share((label.task_completed for label in group), level=level)

    control_errors = [label for label in controls if label.outcome in ERROR_OUTCOMES]
    return RunSummary(
        facts=run_facts(log),
        level=level,
        trials=len(labels),
        control_trials=len(controls),
        template_trials=len(templates),
        attack=attack(templates),
        attack_by_template={
            template_id: attack(t for t in templates if t.template_id == template_id)
            for template_id in template_ids
        },
        delivered=len(delivered),
        attempted=share((t.sent_to_watched_address for t in delivered), level=level),
        completed=share((t.record_leaked for t in delivered), level=level),
        attempt_completion=_attempt_completion(delivered),
        utility_control=completion(controls),
        utility_template=completion(templates),
        utility_by_user_task=tuple(
            UserTaskUtility(
                user_task=task,
                control=completion(c for c in controls if c.user_task == task),
                template=completion(t for t in templates if t.user_task == task),
            )
            for task in user_tasks
        ),
        control=ControlSummary(
            trials=len(controls),
            errors=outcome_counts(control_errors),
            record_leaked=share((c.record_leaked for c in controls), level=level),
            sent_to_watched_address=share(
                (c.sent_to_watched_address for c in controls), level=level
            ),
        ),
        delivery=share((t.note_delivered for t in templates), level=level),
        items=tuple(
            ItemResult(
                user_task=task,
                template_id=template_id,
                counts=outcome_counts(
                    t for t in templates if (t.user_task, t.template_id) == (task, template_id)
                ),
            )
            for task, template_id in items
        ),
        labels=tuple(labels),
    )
