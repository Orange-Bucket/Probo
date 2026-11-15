# SPDX-License-Identifier: Apache-2.0
"""Score the reply-only grader against a deterministic check, and add it to stored logs."""

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, ClassVar, Final, cast

# score's `scorers` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import score  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.log import EvalLog, write_eval_log
from inspect_ai.model import Model
from pydantic import Field, Strict, computed_field

from probo.checks.result import CheckResult, check_result
from probo.judges.reply_only import (
    JUDGE_GENERATE_CONFIG,
    JUDGE_MODEL,
    JUDGE_PROMPT_SHA256,
    JUDGE_PROMPT_VERSION,
    JUDGE_ROLE,
    JUDGE_STATUS,
    SCORER_REPLY_ONLY_JUDGE,
    STATUS_EMPTY_REPLY,
    STATUS_ERROR,
    STATUS_GRADED,
    STATUS_GRADER_INCOMPLETE,
    STATUS_NO_FINAL_REPLY,
    reply_only_judge,
)
from probo.scenarios.helpdesk_exfil.keys import SCORER_RECORD_LEAKED
from probo.stats.base import FrozenModel
from probo.stats.confusion import ConfusionMatrix
from probo.stats.rate import Proportion, format_level

SampleRef = tuple[str | int, int]
"""A trial: sample id and epoch."""

# Not strict, so that JSON arrays load as tuples (the model is otherwise strict).
_Trials = Annotated[tuple[Annotated[SampleRef, Strict(False)], ...], Strict(False)]

INDEPENDENCE_NOTE: Final = (
    "Repeated epochs of one sample are counted as separate trials; "
    "the intervals assume the trials are independent."
)
"""Printed by `JudgeCalibration.render` next to the trial counts."""

STATUSES: Final = (
    STATUS_GRADED,
    STATUS_EMPTY_REPLY,
    STATUS_NO_FINAL_REPLY,
    STATUS_ERROR,
    STATUS_GRADER_INCOMPLETE,
)
"""Every grader status, in the order `render` prints them."""

_RESULT: Final[dict[CheckResult, bool | None]] = {
    CheckResult.TRUE: True,
    CheckResult.FALSE: False,
    CheckResult.NOT_APPLICABLE: None,
}
_EXCLUDED_STATUS: Final = {
    STATUS_NO_FINAL_REPLY: "no_final_reply",
    STATUS_ERROR: "judge_error",
    STATUS_GRADER_INCOMPLETE: "judge_incomplete",
}
"""Grader statuses whose trials are excluded, and the `Exclusions` field counting them."""


_Count = Annotated[int, Field(ge=0)]


class Exclusions(FrozenModel):
    """Trials left out of the pairs, by reason; each trial is counted under the first reason
    that applies, in field order."""

    sample_error: _Count = 0
    """The sample errored (`EvalSample.error`): an eval would not have graded it."""
    reference_missing: _Count = 0
    """The trial has no score from the reference check."""
    judge_missing: _Count = 0
    """The trial has no score from the grader."""
    reference_not_applicable: _Count = 0
    """The reference check does not apply to the trial."""
    no_final_reply: _Count = 0
    """The agent's run did not end in a submission (status `no_final_reply`)."""
    judge_error: _Count = 0
    """The grader call raised (status `error`): an infrastructure failure, not an answer."""
    judge_incomplete: _Count = 0
    """The grader output was cut off, overflowed, filtered or had an error (status
    `grader_incomplete`)."""

    @property
    def total(self) -> int:
        """Number of trials excluded."""
        return sum(getattr(self, name) for name in type(self).model_fields)

    def render(self) -> str:
        """`name count` for every reason, comma separated."""
        return ", ".join(f"{name} {getattr(self, name)}" for name in type(self).model_fields)


class JudgeStatuses(FrozenModel):
    """Number of grader scores in a log by `JUDGE_STATUS`; one field per status in `STATUSES`."""

    graded: _Count = 0
    """The grader answered (`STATUS_GRADED`)."""
    empty_reply: _Count = 0
    """The agent submitted an empty reply (`STATUS_EMPTY_REPLY`)."""
    no_final_reply: _Count = 0
    """The agent's run did not end in a submission (`STATUS_NO_FINAL_REPLY`)."""
    error: _Count = 0
    """The grader call raised (`STATUS_ERROR`)."""
    grader_incomplete: _Count = 0
    """The grader output was unusable (`STATUS_GRADER_INCOMPLETE`)."""


class JudgeCalibration(FrozenModel):
    """The grader against a deterministic reference over one log; build with `calibrate`."""

    judge: str
    """Name of the grader's scorer."""
    reference: str
    """Name of the reference check's scorer."""
    judge_model: str
    """The grader model, the same in every grader score of the log."""
    prompt_version: str
    """The grader prompt version, the same in every grader score of the log."""
    prompt_sha256: str
    """The grader prompt hash, the same in every grader score of the log."""
    generate_config: dict[str, Any] | None
    """The generation settings of the grader calls, the same in every call of the log; None
    when no call completed."""
    matrix: ConfusionMatrix
    """Reference first, grader second; an UNKNOWN grader result is a None prediction."""
    sample_ids: int
    """Number of distinct sample ids among the pairs."""
    epochs: int
    """Number of distinct epochs among the pairs."""
    statuses: JudgeStatuses
    """Number of grader scores in the log by `JUDGE_STATUS`, every status listed."""
    excluded: Exclusions
    """Trials not in `matrix`, by reason."""
    false_positives: _Trials
    """Trials with reference false and grader YES, in log order."""
    false_negatives: _Trials
    """Trials with reference true and grader NO, in log order."""
    unknowns: _Trials
    """Trials in `matrix` where the grader result is UNKNOWN, in log order."""
    level: float = 0.95
    """Confidence level of the rates' intervals."""

    DERIVED: ClassVar[tuple[str, ...]] = (
        "base_rate",
        "precision",
        "recall",
        "recall_unknown_as_miss",
    )

    @computed_field
    @property
    def base_rate(self) -> Proportion | None:
        """`ConfusionMatrix.base_rate` at `level`: share of pairs whose reference is positive."""
        return self.matrix.base_rate(self.level)

    @computed_field
    @property
    def precision(self) -> Proportion | None:
        """`ConfusionMatrix.precision` at `level`: tp / (tp + fp), unknowns excluded."""
        return self.matrix.precision(self.level)

    @computed_field
    @property
    def recall(self) -> Proportion | None:
        """`ConfusionMatrix.recall` at `level`: tp / (tp + fn), unknowns excluded."""
        return self.matrix.recall(self.level)

    @computed_field
    @property
    def recall_unknown_as_miss(self) -> Proportion | None:
        """`ConfusionMatrix.recall_unknown_as_miss` at `level`: unknown positives as misses."""
        return self.matrix.recall_unknown_as_miss(self.level)

    def check_derived(self, name: str, value: object) -> None:
        """Accept a supplied rate only if it equals the one computed from `matrix` and `level`."""
        computed: Proportion | None = getattr(self, name)
        supplied = None if value is None else Proportion.model_validate(value)
        if supplied != computed:
            raise ValueError(f"supplied {name} {supplied} disagrees with computed {computed}")

    def render(self) -> str:
        """ASCII lines: grader, prompt and settings, the trial counts, the matrix and its
        rates (each with n and a Wilson interval), the grader statuses, the exclusions, and
        the disagreeing trials as `id@epoch`."""

        def refs(trials: tuple[SampleRef, ...]) -> str:
            return ", ".join(f"{sample_id}@{epoch}" for sample_id, epoch in trials) or "none"

        statuses = ", ".join(f"{name} {getattr(self.statuses, name)}" for name in STATUSES)
        config = (
            "none"
            if self.generate_config is None
            else json.dumps(self.generate_config, sort_keys=True)
        )
        return "\n".join(
            [
                f"grader {self.judge} ({self.judge_model}, prompt v{self.prompt_version} "
                f"sha256 {self.prompt_sha256[:12]}) against {self.reference}, "
                f"{format_level(self.level)} Wilson intervals",
                f"grader generate config: {config}",
                f"trials: {self.matrix.total} pairs from {self.sample_ids} sample ids over "
                f"{self.epochs} epochs. {INDEPENDENCE_NOTE}",
                self.matrix.render(self.level),
                f"grader statuses: {statuses}",
                f"excluded: {self.excluded.total} ({self.excluded.render()})",
                f"false positives ({len(self.false_positives)}): {refs(self.false_positives)}",
                f"false negatives ({len(self.false_negatives)}): {refs(self.false_negatives)}",
                f"unknown ({len(self.unknowns)}): {refs(self.unknowns)}",
            ]
        )


@dataclass
class _Collected:
    rows: list[tuple[SampleRef, bool, bool | None]] = field(default_factory=lambda: [])
    """Trial, reference result and grader result of every pair, in log order."""
    excluded: Counter[str] = field(default_factory=lambda: Counter[str]())
    statuses: Counter[str] = field(default_factory=lambda: Counter[str]())
    identities: set[tuple[str, str, str]] = field(
        default_factory=lambda: set[tuple[str, str, str]]()
    )
    configs: dict[str, dict[str, Any]] = field(default_factory=lambda: {})
    """Distinct generate configs of the grader calls, by their canonical JSON."""


def _identity(metadata: dict[str, Any], judge: str) -> tuple[str, str, str]:
    values = (
        metadata.get(JUDGE_MODEL),
        metadata.get(JUDGE_PROMPT_VERSION),
        metadata.get(JUDGE_PROMPT_SHA256),
    )
    model, version, sha256 = values
    if not (isinstance(model, str) and isinstance(version, str) and isinstance(sha256, str)):
        raise ValueError(f"a {judge!r} score lacks its grader model, prompt version or hash")
    return model, version, sha256


def _collect(log: EvalLog, judge: str, reference: str) -> _Collected:
    if log.samples is None:
        raise ValueError("the log has no samples (was it read with header_only=True?)")
    found = _Collected()
    for sample in log.samples:
        scores = sample.scores or {}
        judged = scores.get(judge)
        status = None
        if judged is not None:
            metadata = dict(judged.metadata or {})
            found.identities.add(_identity(metadata, judge))
            status = metadata.get(JUDGE_STATUS)
            if status not in STATUSES:
                raise ValueError(f"a {judge!r} score has an unknown status {status!r}")
            found.statuses[str(status)] += 1
            config = metadata.get(JUDGE_GENERATE_CONFIG)
            if isinstance(config, dict):
                settings = cast("dict[str, Any]", config)
                found.configs[json.dumps(settings, sort_keys=True)] = settings
        checked = scores.get(reference)
        if sample.error is not None:
            found.excluded["sample_error"] += 1
        elif checked is None:
            found.excluded["reference_missing"] += 1
        elif judged is None:
            found.excluded["judge_missing"] += 1
        elif (truth := _RESULT[check_result(checked)]) is None:
            found.excluded["reference_not_applicable"] += 1
        elif status in _EXCLUDED_STATUS:
            found.excluded[_EXCLUDED_STATUS[str(status)]] += 1
        else:
            found.rows.append(((sample.id, sample.epoch), truth, _RESULT[check_result(judged)]))
    return found


def judge_pairs(
    log: EvalLog,
    judge: str = SCORER_REPLY_ONLY_JUDGE,
    reference: str = SCORER_RECORD_LEAKED,
) -> list[tuple[bool, bool | None]]:
    """(reference, grader) results of every trial that has both, in log order.

    An UNKNOWN grader result (including an empty reply) is None. Left out (see
    `Exclusions`): errored samples, trials missing either score, trials where the reference
    is not applicable, and trials with no final reply, a raising grader call or incomplete
    grader output.

    Raises:
        ValueError: If the log has no samples loaded, a score has no check result, or a
            grader score has no grader identity or an unknown status.
    """
    return [(truth, guess) for _, truth, guess in _collect(log, judge, reference).rows]


def calibrate(
    log: EvalLog,
    judge: str = SCORER_REPLY_ONLY_JUDGE,
    reference: str = SCORER_RECORD_LEAKED,
    level: float = 0.95,
) -> JudgeCalibration:
    """The grader's confusion matrix against the reference check, with what was excluded.

    Raises:
        ValueError: If the log has no samples loaded; has no `judge` scores; has `judge`
            scores from more than one grader model, prompt version, prompt hash or generate
            config; or leaves no pair (for example every grader call failed), so that an
            all-error run cannot pass for one where the grader always abstained.
    """
    found = _collect(log, judge, reference)
    if not found.identities:
        raise ValueError(f"the log has no {judge!r} scores")
    if len(found.identities) > 1:
        seen = "; ".join(
            f"model {m}, prompt v{v} sha256 {h}" for m, v, h in sorted(found.identities)
        )
        raise ValueError(f"the log mixes {judge!r} graders or prompts: {seen}")
    if len(found.configs) > 1:
        raise ValueError(f"the log mixes {judge!r} generate configs: {sorted(found.configs)}")
    if not found.rows:
        statuses = ", ".join(f"{name} {found.statuses[name]}" for name in STATUSES)
        raise ValueError(
            f"no {judge!r} / {reference!r} pairs in the log; grader statuses: {statuses}; "
            f"excluded: {Exclusions(**found.excluded).render()}"
        )
    ((judge_model, prompt_version, prompt_sha256),) = found.identities

    def trials(truths: tuple[bool, ...], predicted: bool | None) -> tuple[SampleRef, ...]:
        return tuple(t for t, truth, guess in found.rows if truth in truths and guess is predicted)

    return JudgeCalibration(
        judge=judge,
        reference=reference,
        judge_model=judge_model,
        prompt_version=prompt_version,
        prompt_sha256=prompt_sha256,
        generate_config=next(iter(found.configs.values()), None),
        matrix=ConfusionMatrix.from_pairs((truth, guess) for _, truth, guess in found.rows),
        sample_ids=len({sample_id for (sample_id, _), _, _ in found.rows}),
        epochs=len({epoch for (_, epoch), _, _ in found.rows}),
        statuses=JudgeStatuses(**{name: found.statuses[name] for name in STATUSES}),
        excluded=Exclusions(**found.excluded),
        false_positives=trials((False,), True),
        false_negatives=trials((True,), False),
        unknowns=trials((True, False), None),
        level=level,
    )


def add_judge_scores(log: EvalLog, judge_model: str | Model, output: str | Path) -> EvalLog:
    """Add `reply_only_judge` scores to a stored log without running the agent again.

    Runs `inspect_ai.score(log, reply_only_judge(), model_roles={"judge": judge_model},
    action="append")`, which rebuilds each sample's state from the log and keeps its
    transcript and existing scores, then writes the result to `output` (never over `log`'s
    own file unless `output` names it) and returns it. Samples that errored are scored too,
    as `score` does, and `calibrate` excludes them. The equivalent recipe by hand::

        log = read_eval_log(path)
        scored = inspect_ai.score(log, reply_only_judge(),
                                  model_roles={"judge": "provider/model"}, action="append")
        write_eval_log(scored, out_path)

    Raises:
        ValueError: If the log has no samples loaded or already has grader scores (an
            append would add a second, renamed grader scorer instead).
    """
    if log.samples is None:
        raise ValueError("the log has no samples (was it read with header_only=True?)")
    if any(SCORER_REPLY_ONLY_JUDGE in (s.scores or {}) for s in log.samples):
        raise ValueError(f"the log already has {SCORER_REPLY_ONLY_JUDGE!r} scores")
    scored = score(
        log,
        reply_only_judge(),
        model_roles={JUDGE_ROLE: judge_model},
        action="append",
        display="none",
    )
    write_eval_log(scored, str(output))
    return scored
