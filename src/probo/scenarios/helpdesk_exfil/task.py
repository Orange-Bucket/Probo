# SPDX-License-Identifier: Apache-2.0
"""The `helpdesk_exfil` Inspect task (scenario id `helpdesk-exfil`)."""

import secrets
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from inspect_ai import Task, task

from probo.attacks import Corpus, load_corpus, load_corpus_from
from probo.scenarios.helpdesk_exfil.agent import helpdesk_agent
from probo.scenarios.helpdesk_exfil.dataset import build_dataset
from probo.scenarios.helpdesk_exfil.keys import (
    META_CORPUS_HASH,
    META_CORPUS_VERSION,
    META_SCENARIO,
    SCENARIO_ID,
)
from probo.scenarios.helpdesk_exfil.leak_checks import (
    note_delivered,
    record_leaked,
    sent_to_watched_address,
)
from probo.scenarios.helpdesk_exfil.scorer import task_completed
from probo.scenarios.helpdesk_exfil.startup import setup_environment

DEFAULT_MESSAGE_LIMIT: Final = 40
"""Per-sample message limit unless the task is given another."""
DEFAULT_WATCH_ADDRESS: Final = "collector@outside.test"
"""Address watched by default: on a reserved domain, and no customer's address."""
DEFAULT_CORPUS_VERSION: Final = "2026-11"
"""Version of the packaged template corpus used by default."""
CORPUS_FAMILY: Final = "static"
"""Template family this task draws from."""


def template_ids(templates: str | Sequence[str] | None) -> list[str] | None:
    """`templates` as a list of ids: a comma-separated string (the `-T templates=a,b` form)
    is split and stripped; None stays None."""
    if templates is None:
        return None
    if isinstance(templates, str):
        return [part.strip() for part in templates.split(",") if part.strip()]
    return list(templates)


def task_corpus(corpus_version: str, corpus_dir: str | None) -> Corpus:
    """The packaged corpus `corpus_version`, or the one in `corpus_dir` labelled with it."""
    if corpus_dir is None:
        return load_corpus(CORPUS_FAMILY, corpus_version)
    return load_corpus_from(Path(corpus_dir), family=CORPUS_FAMILY, version=corpus_version)


@task
def helpdesk_exfil(
    seed: int | None = None,
    message_limit: int = DEFAULT_MESSAGE_LIMIT,
    watch_address: str | None = DEFAULT_WATCH_ADDRESS,
    corpus_version: str = DEFAULT_CORPUS_VERSION,
    templates: str | Sequence[str] | None = None,
    corpus_dir: str | None = None,
) -> Task:
    """A helpdesk agent answers support tickets by e-mail.

    The dataset crosses every user task with a control sample (default ticket note) and one
    sample per selected corpus template (see `dataset.build_dataset`). Scored by
    `task_completed` (utility) and the three leak checks in `leak_checks`:
    `record_leaked`, `sent_to_watched_address` and `note_delivered`.

    Args:
        seed: Seed for the per-record marker tokens. When omitted, one is drawn at random
            when the task is built and recorded in every sample's metadata (`seed`), which
            is the only source of truth for reproducing tokens. It is not put in the task
            metadata: `eval_retry` rebuilds the task from the passed arguments, so an
            unseeded run draws a new seed for the retried samples while carried-over samples
            keep theirs.
        message_limit: Per-sample message limit for the agent.
        watch_address: Address recorded in every sample for `sent_to_watched_address` and
            given to templates as `{watch_address}`; None watches nothing.
        corpus_version: Dated version of the template corpus.
        templates: Ids of the templates to use, as a list or a comma-separated string;
            all of the corpus when omitted.
        corpus_dir: Directory of template files to use instead of the packaged corpus.
    """
    if seed is None:
        seed = secrets.randbits(63)
    corpus = task_corpus(corpus_version, corpus_dir)
    return Task(
        dataset=build_dataset(
            seed, watch_address=watch_address, corpus=corpus, templates=template_ids(templates)
        ),
        setup=setup_environment(),
        solver=helpdesk_agent(),
        scorer=[task_completed(), record_leaked(), sent_to_watched_address(), note_delivered()],
        message_limit=message_limit,
        metadata={
            META_SCENARIO: SCENARIO_ID,
            META_CORPUS_VERSION: corpus.version,
            META_CORPUS_HASH: corpus.content_hash,
        },
    )
