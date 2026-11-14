# SPDX-License-Identifier: Apache-2.0
"""Marker tokens and seeds: per (sample, epoch, customer), reproducible from the run seed."""

from pathlib import Path

from inspect_ai.log import EvalLog, read_eval_log

from probo.checks.canary import derive_canary, is_canary
from probo.scenarios.helpdesk_exfil.environment import Customer
from probo.scenarios.helpdesk_exfil.keys import META_SEED, STORE_CUSTOMERS

from .helpdesk_support import run

TokenKey = tuple[str, int, str]


def tokens(log: EvalLog) -> dict[TokenKey, str]:
    """Recovery code of every customer, keyed by (sample id, epoch, customer id)."""
    assert log.samples is not None
    found: dict[TokenKey, str] = {}
    for sample in log.samples:
        for customer in map(Customer.model_validate, sample.store[STORE_CUSTOMERS]):
            found[(str(sample.id), sample.epoch, customer.id)] = customer.recovery_code
    return found


def test_tokens_differ_by_customer_sample_and_epoch(tmp_path: Path) -> None:
    """Every (sample, epoch, customer) gets its own token, derived from the seed."""
    found = tokens(run(tmp_path, task_args={"seed": 11}, epochs=2))
    assert {epoch for _, epoch, _ in found} == {1, 2}
    assert len({sample_id for sample_id, _, _ in found}) == 2
    assert len(found) == 2 * 2 * 3
    assert len(set(found.values())) == len(found)
    for (sample_id, epoch, customer_id), token in found.items():
        assert is_canary(token)
        assert token == derive_canary(11, sample_id, epoch, customer_id)


def test_same_seed_repeats_tokens_and_other_seed_changes_them(tmp_path: Path) -> None:
    """Two runs with one seed give identical tokens; a different seed shares none."""
    first = tokens(run(tmp_path / "a", task_args={"seed": 5}))
    again = tokens(run(tmp_path / "b", task_args={"seed": 5}))
    other = tokens(run(tmp_path / "c", task_args={"seed": 6}))
    assert first == again
    assert first.keys() == other.keys()
    assert not set(first.values()) & set(other.values())


def test_drawn_seed_is_recorded_in_the_log(tmp_path: Path) -> None:
    """Without a seed, the drawn one is in task and sample metadata and reproduces the tokens."""
    log = read_eval_log(run(tmp_path).location)
    assert log.eval.metadata is not None
    seed = log.eval.metadata[META_SEED]
    assert isinstance(seed, int)
    assert log.samples is not None
    assert all(sample.metadata[META_SEED] == seed for sample in log.samples)
    for (sample_id, epoch, customer_id), token in tokens(log).items():
        assert token == derive_canary(seed, sample_id, epoch, customer_id)


def test_unseeded_runs_draw_different_seeds(tmp_path: Path) -> None:
    """Each unseeded run draws its own seed."""
    seeds = [run(tmp_path / name).eval.metadata for name in ("a", "b")]
    assert seeds[0] is not None
    assert seeds[1] is not None
    assert seeds[0][META_SEED] != seeds[1][META_SEED]
