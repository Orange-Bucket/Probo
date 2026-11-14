# SPDX-License-Identifier: Apache-2.0
"""Contract: model_roles bind named roles that get_model(role=...) resolves per sample."""

from collections import Counter
from pathlib import Path

from inspect_ai import Task
from inspect_ai.dataset import Sample
from inspect_ai.event import ModelEvent
from inspect_ai.log import EvalSample
from inspect_ai.model import get_model
from inspect_ai.scorer import Score, Scorer, Target, mean, scorer
from inspect_ai.solver import TaskState, generate

from .fixtures.support import MOCK_MODEL, only_sample, run_eval, scripted


@scorer(metrics=[mean()])
def ask_roles() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        replies: dict[str, str] = {}
        for role in ("judge", "target", "missing"):
            replies[role] = (await get_model(role=role).generate("q")).completion
        replies["active"] = (await get_model().generate("q")).completion
        replies["defaulted"] = (
            await get_model(role="missing", default=scripted("DEFAULT")).generate("q")
        ).completion
        try:
            get_model(role="missing", required=True)
            replies["required"] = "no error"
        except Exception as error:
            replies["required"] = f"{type(error).__name__}: {error}"
        return Score(value=1.0, metadata=replies)

    return score


def run(tmp_path: Path) -> EvalSample:
    log = run_eval(
        Task(dataset=[Sample(input="hi")], solver=[generate()], scorer=ask_roles()),
        tmp_path,
        scripted("MAIN"),
        model_roles={"judge": scripted("JUDGE"), "target": scripted("TARGET")},
    )
    return only_sample(log)


def role_replies(sample: EvalSample) -> dict[str, str]:
    assert sample.scores is not None
    metadata = sample.scores["ask_roles"].metadata
    assert metadata is not None
    return {str(k): str(v) for k, v in metadata.items()}


def test_roles_resolve_to_distinct_models(tmp_path: Path) -> None:
    """get_model(role=r) returns the model bound to r in eval(model_roles=...)."""
    replies = role_replies(run(tmp_path))
    assert replies["judge"] == "JUDGE"
    assert replies["target"] == "TARGET"
    assert replies["active"] == "MAIN"


def test_unbound_role_falls_back_to_active_model(tmp_path: Path) -> None:
    """An unbound role silently returns the eval's main model unless default= or required=."""
    replies = role_replies(run(tmp_path))
    assert replies["missing"] == "MAIN"
    assert replies["defaulted"] == "DEFAULT"
    assert replies["required"] == (
        "PrerequisiteError: Model role 'missing' is required and was not specified."
    )


def test_role_is_recorded_on_model_events_and_role_usage(tmp_path: Path) -> None:
    """ModelEvent.role names the role (default= models take the role, fallbacks do not)."""
    sample = run(tmp_path)
    roles = [e.role for e in sample.events if isinstance(e, ModelEvent)]
    assert Counter(roles) == Counter({None: 3, "judge": 1, "target": 1, "missing": 1})
    assert set(sample.role_usage) == {"judge", "missing", "target"}
    assert list(sample.model_usage) == [MOCK_MODEL]
    role_total = sum(u.total_tokens for u in sample.role_usage.values())
    assert sample.model_usage[MOCK_MODEL].total_tokens > role_total
