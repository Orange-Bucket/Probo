# SPDX-License-Identifier: Apache-2.0
"""Marker tokens and seeds: per (sample, epoch, customer), reproducible from sample metadata."""

from pathlib import Path

# eval_retry's `scanner` parameter is typed via the optional inspect_scout package (not installed).
from inspect_ai import eval_retry  # pyright: ignore[reportUnknownVariableType]
from inspect_ai.log import EvalLog, read_eval_log
from inspect_ai.model import (
    ChatMessage,
    ChatMessageUser,
    GenerateConfig,
    ModelOutput,
    get_model,
)
from inspect_ai.tool import ToolChoice, ToolInfo

from probo.checks.canary import derive_canary, is_canary
from probo.scenarios.helpdesk_exfil.environment import Customer
from probo.scenarios.helpdesk_exfil.keys import META_SEED, SCENARIO_ID, STORE_CUSTOMERS
from probo.scenarios.helpdesk_exfil.startup import marker_token

from .helpdesk_support import MOCK_MODEL, run

TokenKey = tuple[str, int, str]


def tokens(log: EvalLog) -> dict[TokenKey, str]:
    """Recovery code of every customer, keyed by (sample id, epoch, customer id)."""
    assert log.samples is not None
    found: dict[TokenKey, str] = {}
    for sample in log.samples:
        for customer in map(Customer.model_validate, sample.store[STORE_CUSTOMERS]):
            found[(str(sample.id), sample.epoch, customer.id)] = customer.recovery_code
    return found


def assert_reproducible_from_sample_metadata(log: EvalLog) -> None:
    """Every logged token equals marker_token() over that sample's own metadata seed."""
    assert log.samples
    for sample in log.samples:
        seed = sample.metadata[META_SEED]
        assert isinstance(seed, int)
        for customer in map(Customer.model_validate, sample.store[STORE_CUSTOMERS]):
            expected = marker_token(seed, sample.id, sample.epoch, customer.id)
            assert customer.recovery_code == expected


def test_marker_token_includes_the_scenario_id() -> None:
    """The scenario id is a derivation part, so another scenario cannot collide."""
    token = marker_token(1, "s/none", 1, "C-001")
    assert is_canary(token)
    assert token == derive_canary(1, SCENARIO_ID, "s/none", 1, "C-001")
    assert token != derive_canary(1, "s/none", 1, "C-001")


def test_tokens_differ_by_customer_sample_and_epoch(tmp_path: Path) -> None:
    """Every (sample, epoch, customer) gets its own token, derived from the seed."""
    found = tokens(run(tmp_path, task_args={"seed": 11}, epochs=2))
    assert {epoch for _, epoch, _ in found} == {1, 2}
    assert len({sample_id for sample_id, _, _ in found}) == 2
    assert len(found) == 2 * 2 * 3
    assert len(set(found.values())) == len(found)
    for (sample_id, epoch, customer_id), token in found.items():
        assert token == marker_token(11, sample_id, epoch, customer_id)


def test_same_seed_repeats_tokens_and_other_seed_changes_them(tmp_path: Path) -> None:
    """Two runs with one seed give identical tokens; a different seed shares none."""
    first = tokens(run(tmp_path / "a", task_args={"seed": 5}))
    again = tokens(run(tmp_path / "b", task_args={"seed": 5}))
    other = tokens(run(tmp_path / "c", task_args={"seed": 6}))
    assert first == again
    assert first.keys() == other.keys()
    assert not set(first.values()) & set(other.values())


def test_unseeded_run_is_reproducible_from_sample_metadata_alone(tmp_path: Path) -> None:
    """The drawn seed is in every sample's metadata (not the task's) and rebuilds the tokens."""
    log = read_eval_log(run(tmp_path).location)
    assert META_SEED not in (log.eval.metadata or {})
    assert log.samples is not None
    assert len({sample.metadata[META_SEED] for sample in log.samples}) == 1
    assert_reproducible_from_sample_metadata(log)


def test_unseeded_runs_draw_different_seeds(tmp_path: Path) -> None:
    """Each unseeded run draws its own seed."""
    seeds: list[int] = []
    for name in ("a", "b"):
        samples = run(tmp_path / name).samples
        assert samples is not None
        seeds.append(samples[0].metadata[META_SEED])
    assert seeds[0] != seeds[1]


def fail_delivery_date_sample(
    messages: list[ChatMessage],
    tools: list[ToolInfo],
    tool_choice: ToolChoice,
    config: GenerateConfig,
) -> ModelOutput:
    """Errors the reply-delivery-date sample; submits at once in the other."""
    prompt = next(m for m in messages if isinstance(m, ChatMessageUser)).text
    if "T-1002" in prompt:
        raise RuntimeError("model failure")
    return ModelOutput.for_tool_call(MOCK_MODEL, "submit", {"answer": "done"})


def test_retry_mixes_seeds_and_sample_metadata_still_reproduces(tmp_path: Path) -> None:
    """After eval_retry of an unseeded run, carried-over and retried samples have different
    seeds, which is why only the per-sample seed may be used to reproduce tokens."""
    model = get_model(MOCK_MODEL, custom_outputs=fail_delivery_date_sample)
    failed = run(tmp_path, model, status="error")
    (retried,) = eval_retry(failed, log_dir=str(tmp_path), display="none")
    assert retried.status == "success"
    assert retried.samples is not None
    seeds = {str(sample.id): sample.metadata[META_SEED] for sample in retried.samples}
    assert seeds["reply-delivery-date/none"] != seeds["reply-order-status/none"]
    assert_reproducible_from_sample_metadata(retried)
