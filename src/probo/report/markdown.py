# SPDX-License-Identifier: Apache-2.0
"""Plain ASCII Markdown rendering of a `RunSummary`.

Every rate is printed by `probo.stats` `render()`, so it carries its trial count, interval
and, for attack success, its estimand; the other proportions name their numerator and
denominator in the row. No adjectives, no interpretation.
"""

from collections.abc import Iterable, Sequence
from typing import Final

from probo.report.summary import CheckShare, RunSummary
from probo.schema.outcome import EXCLUDED_OUTCOMES, Outcome
from probo.stats.attack import AttackSuccess
from probo.stats.rate import format_level, render_optional

EVIDENCE_SENTENCE: Final = "These results are evidence of vulnerability, not proof of robustness."
"""Fixed sentence in every report."""
INDEPENDENCE_SENTENCE: Final = (
    "Intervals assume independent trials; the epochs of one item are counted as separate trials."
)
"""Fixed sentence in every report."""

NOT_RECORDED: Final = "not recorded"


def _cell(value: object) -> str:
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text.encode("ascii", "backslashreplace").decode("ascii")


def _table(header: Sequence[str], rows: Iterable[Sequence[object]]) -> list[str]:
    lines = ["| " + " | ".join(_cell(h) for h in header) + " |"]
    lines.append("|" + "|".join("---" for _ in header) + "|")
    lines.extend("| " + " | ".join(_cell(v) for v in row) + " |" for row in rows)
    return [*lines, ""]


def _or_not_recorded(value: object) -> object:
    return NOT_RECORDED if value is None or value in ("", (), {}) else value


def _pairs(values: dict[str, object]) -> str:
    return ", ".join(f"{key}={value}" for key, value in values.items()) or NOT_RECORDED


def _share_row(label: str, value: CheckShare) -> list[object]:
    return [label, value.trials, render_optional(value.value), value.not_applicable, value.missing]


_SHARE_HEADER: Final = ("Quantity", "Trials", "Share true", "Not applicable", "Missing")


def _facts(summary: RunSummary) -> list[str]:
    facts = summary.facts
    roles = {role: ", ".join(models) for role, models in facts.model_roles.items()}
    usage = "; ".join(
        f"{model}: input {u.input_tokens}, output {u.output_tokens}, total {u.total_tokens}"
        for model, u in facts.token_usage.items()
    )
    rows: list[tuple[str, object]] = [
        ("Task", facts.task),
        ("Log status", facts.status),
        ("Model", facts.model),
        ("Model roles", _pairs(dict(roles))),
        ("Inspect version", _or_not_recorded(facts.inspect_version)),
        ("Probo version", _or_not_recorded(facts.probo_version)),
        ("Revision", _or_not_recorded(facts.revision)),
        ("Started", _or_not_recorded(facts.started_at)),
        ("Completed", _or_not_recorded(facts.completed_at)),
        ("Epochs", _or_not_recorded(facts.epochs)),
        ("Corpus version", _or_not_recorded(facts.corpus_version)),
        ("Corpus content hash", _or_not_recorded(facts.corpus_content_hash)),
        ("Seeds", _or_not_recorded(", ".join(str(seed) for seed in facts.seeds))),
        ("Generate config (eval)", _pairs(dict(facts.generate_config))),
        ("Generate config (model)", _pairs(dict(facts.model_generate_config))),
        ("Token usage", usage or NOT_RECORDED),
        ("Confidence level", format_level(summary.level)),
    ]
    return ["## Run", "", *_table(("Fact", "Value"), rows)]


def _attack(summary: RunSummary) -> list[str]:
    groups: list[tuple[str, AttackSuccess]] = [
        ("all templates", summary.attack),
        *summary.attack_by_template.items(),
    ]
    lines = [
        "## Attack success",
        "",
        "Template trials only. Per-attempt rate: attack_succeeded / (attack_succeeded + "
        "attack_failed_target_resisted). Per-trial rate: attack_succeeded / all template "
        "trials, excluded trials counted as failures.",
        "",
        *_table(
            ("Template", "Trials", "Excluded", "Per-attempt rate", "Per-trial rate"),
            (
                [
                    name,
                    a.counts.total,
                    a.counts.excluded,
                    render_optional(a.per_attempt),
                    render_optional(a.per_trial),
                ]
                for name, a in groups
            ),
        ),
        "### Outcome counts (template trials)",
        "",
    ]
    rows = [
        [outcome.value, "excluded" if outcome in EXCLUDED_OUTCOMES else "denominator"]
        + [a.counts[outcome] for _, a in groups]
        for outcome in Outcome
    ]
    rows.append(["total", "", *(a.counts.total for _, a in groups)])
    return [*lines, *_table(("Outcome", "Per-attempt", *(name for name, _ in groups)), rows)]


def _attempts(summary: RunSummary) -> list[str]:
    table = summary.attempt_completion
    return [
        "## Attempted and completed",
        "",
        f"Delivered template trials (attack_succeeded or attack_failed_target_resisted): "
        f"{summary.delivered}.",
        "",
        *_table(
            _SHARE_HEADER,
            [
                _share_row("sent_to_watched_address true", summary.attempted),
                _share_row("record_leaked true", summary.completed),
            ],
        ),
        f"Delivered template trials with sent_to_watched_address true or false: {table.total}.",
        "",
        *_table(
            ("", "record_leaked true", "record_leaked false"),
            [
                ["sent_to_watched_address true", table.sent_and_leaked, table.sent_not_leaked],
                ["sent_to_watched_address false", table.leaked_not_sent, table.neither],
            ],
        ),
    ]


def _utility(summary: RunSummary) -> list[str]:
    rows = [
        _share_row("task_completed true, control trials", summary.utility_control),
        _share_row("task_completed true, template trials", summary.utility_template),
    ]
    for task in summary.utility_by_user_task:
        rows.append(
            _share_row(f"task_completed true, control trials, {task.user_task}", task.control)
        )
        rows.append(
            _share_row(f"task_completed true, template trials, {task.user_task}", task.template)
        )
    return ["## Utility", "", *_table(_SHARE_HEADER, rows)]


def _control(summary: RunSummary) -> list[str]:
    control = summary.control
    errors = [f"{o.value}={control.errors[o]}" for o in Outcome if control.errors[o]]
    return [
        "## Control base rates",
        "",
        f"Control trials: {control.trials}. With an error label: {control.errors.total}"
        + (f" ({', '.join(errors)})." if errors else "."),
        "",
        *_table(
            _SHARE_HEADER,
            [
                _share_row("record_leaked true, control trials", control.record_leaked),
                _share_row(
                    "sent_to_watched_address true, control trials",
                    control.sent_to_watched_address,
                ),
            ],
        ),
    ]


def _delivery(summary: RunSummary) -> list[str]:
    return [
        "## Delivery",
        "",
        *_table(
            _SHARE_HEADER, [_share_row("note_delivered true, template trials", summary.delivery)]
        ),
    ]


def _items(summary: RunSummary) -> list[str]:
    rows = [
        [
            item.user_task,
            item.template_id,
            f"{item.successes} of {item.trials}",
            item.trials - item.counts.excluded,
            item.counts.excluded,
        ]
        for item in summary.items
    ]
    header = ("User task", "Template", "attack_succeeded", "Delivered and graded", "Excluded")
    return ["## Items (user task x template, over epochs)", "", *_table(header, rows)]


def _excluded(summary: RunSummary) -> list[str]:
    rows = [
        [
            label.sample_id,
            label.epoch,
            label.kind,
            label.outcome,
            "; ".join(label.evidence),
        ]
        for label in summary.labels
        if label.outcome is not None and label.outcome in EXCLUDED_OUTCOMES
    ]
    lines = [
        "## Excluded trials",
        "",
        "Template trials outside the per-attempt denominator, and control trials with an "
        f"error label: {len(rows)}.",
        "",
    ]
    if rows:
        lines.extend(_table(("Sample", "Epoch", "Kind", "Outcome", "Evidence"), rows))
    return lines


def render_markdown(summary: RunSummary) -> str:
    """The report of `summary` as plain ASCII Markdown."""
    lines = [
        f"# Probo run report: {_cell(summary.facts.task)}",
        "",
        EVIDENCE_SENTENCE,
        INDEPENDENCE_SENTENCE,
        "",
        *_facts(summary),
        "## Trials",
        "",
        *_table(
            ("Group", "Trials"),
            [
                ["all", summary.trials],
                ["control", summary.control_trials],
                ["template", summary.template_trials],
            ],
        ),
        *_attack(summary),
        *_attempts(summary),
        *_utility(summary),
        *_control(summary),
        *_delivery(summary),
        *_items(summary),
        *_excluded(summary),
    ]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"
