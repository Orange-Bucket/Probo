# SPDX-License-Identifier: Apache-2.0
"""Score the reply-only grader against a deterministic check, and add it to stored logs."""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Final

# score's `scorers` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import score  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.log import EvalLog, write_eval_log
from inspect_ai.model import Model
from inspect_ai.scorer import Score
from pydantic import Strict

from probo.checks.result import CheckResult, check_result
from probo.judges.reply_only import (
    JUDGE_MODEL,
    JUDGE_PROMPT_SHA256,
    JUDGE_PROMPT_VERSION,
    JUDGE_ROLE,
    JUDGE_STATUS,
    SCORER_REPLY_ONLY_JUDGE,
    STATUS_ERROR,
    reply_only_judge,
)
from probo.scenarios.helpdesk_exfil.keys import SCORER_RECORD_LEAKED
from probo.stats.base import FrozenModel
from probo.stats.confusion import ConfusionMatrix
from probo.stats.rate import format_level

SampleRef = tuple[str | int, int]
"""A trial: sample id and epoch."""

# Not strict, so that JSON arrays load as tuples (the model is otherwise strict).
_Trials = Annotated[tuple[Annotated[SampleRef, Strict(False)], ...], Strict(False)]

_RESULT: Final[dict[CheckResult, bool | None]] = {
    CheckResult.TRUE: True,
    CheckResult.FALSE: False,
    CheckResult.NOT_APPLICABLE: None,
}


class Exclusions(FrozenModel):
    """Trials left out of the pairs, by reason; each trial is counted under the first reason
    that applies, in field order."""

    reference_missing: int = 0
    """The trial has no score from the reference check."""
    judge_missing: int = 0
    """The trial has no score from the grader."""
    reference_not_applicable: int = 0
    """The reference check does not apply to the trial."""
    judge_error: int = 0
    """The grader call raised (status `error`): an infrastructure failure, not an answer."""

    @property
    def total(self) -> int:
        """Number of trials excluded."""
        return (
            self.reference_missing
            + self.judge_missing
            + self.reference_not_applicable
            + self.judge_error
        )


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
    matrix: ConfusionMatrix
    """Reference first, grader second; an UNKNOWN grader result is a None prediction."""
    excluded: Exclusions
    """Trials not in `matrix`, by reason."""
    false_positives: _Trials
    """Trials with reference false and grader YES, in log order."""
    false_negatives: _Trials
    """Trials with reference true and grader NO, in log order."""
    unknowns: _Trials
    """Trials in `matrix` where the grader result is UNKNOWN, in log order."""
    level: float = 0.95
    """Confidence level of the intervals `render` prints."""

    def render(self) -> str:
        """ASCII lines: grader and prompt, the matrix and its rates (each with n and a Wilson
        interval), the exclusions, and the disagreeing trials as `id@epoch`."""

        def refs(trials: tuple[SampleRef, ...]) -> str:
            return ", ".join(f"{sample_id}@{epoch}" for sample_id, epoch in trials) or "none"

        excluded = self.excluded
        return "\n".join(
            [
                f"grader {self.judge} ({self.judge_model}, prompt v{self.prompt_version} "
                f"sha256 {self.prompt_sha256[:12]}) against {self.reference}, "
                f"{format_level(self.level)} Wilson intervals",
                self.matrix.render(self.level),
                f"excluded: {excluded.total} (reference missing {excluded.reference_missing}, "
                f"judge missing {excluded.judge_missing}, reference not applicable "
                f"{excluded.reference_not_applicable}, judge error {excluded.judge_error})",
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
    prompts: set[tuple[str, str, str]] = field(default_factory=lambda: set[tuple[str, str, str]]())


def _metadata_text(score: Score, key: str) -> str:
    return str((score.metadata or {}).get(key))


def _collect(log: EvalLog, judge: str, reference: str) -> _Collected:
    if log.samples is None:
        raise ValueError("the log has no samples (was it read with header_only=True?)")
    found = _Collected()
    for sample in log.samples:
        scores = sample.scores or {}
        judged = scores.get(judge)
        if judged is not None:
            found.prompts.add(
                (
                    _metadata_text(judged, JUDGE_MODEL),
                    _metadata_text(judged, JUDGE_PROMPT_VERSION),
                    _metadata_text(judged, JUDGE_PROMPT_SHA256),
                )
            )
        checked = scores.get(reference)
        if checked is None:
            found.excluded["reference_missing"] += 1
        elif judged is None:
            found.excluded["judge_missing"] += 1
        elif (truth := _RESULT[check_result(checked)]) is None:
            found.excluded["reference_not_applicable"] += 1
        elif (judged.metadata or {}).get(JUDGE_STATUS) == STATUS_ERROR:
            found.excluded["judge_error"] += 1
        else:
            found.rows.append(((sample.id, sample.epoch), truth, _RESULT[check_result(judged)]))
    return found


def judge_pairs(
    log: EvalLog,
    judge: str = SCORER_REPLY_ONLY_JUDGE,
    reference: str = SCORER_RECORD_LEAKED,
) -> list[tuple[bool, bool | None]]:
    """(reference, grader) results of every trial that has both, in log order.

    An UNKNOWN grader result is None. Left out: trials missing either score, trials where
    the reference is not applicable, and trials whose grader call raised (see `Exclusions`).

    Raises:
        ValueError: If the log has no samples loaded, or a score has no check result.
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
        ValueError: If the log has no samples loaded, no `judge` scores, or `judge` scores
            from more than one grader model, prompt version or prompt hash.
    """
    found = _collect(log, judge, reference)
    if not found.prompts:
        raise ValueError(f"the log has no {judge!r} scores")
    if len(found.prompts) > 1:
        seen = "; ".join(f"model {m}, prompt v{v} sha256 {h}" for m, v, h in sorted(found.prompts))
        raise ValueError(f"the log mixes {judge!r} graders or prompts: {seen}")
    ((judge_model, prompt_version, prompt_sha256),) = found.prompts

    def trials(truths: tuple[bool, ...], predicted: bool | None) -> tuple[SampleRef, ...]:
        return tuple(t for t, truth, guess in found.rows if truth in truths and guess is predicted)

    return JudgeCalibration(
        judge=judge,
        reference=reference,
        judge_model=judge_model,
        prompt_version=prompt_version,
        prompt_sha256=prompt_sha256,
        matrix=ConfusionMatrix.from_pairs((truth, guess) for _, truth, guess in found.rows),
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
    own file unless `output` names it) and returns it. The equivalent recipe by hand::

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
