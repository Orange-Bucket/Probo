# SPDX-License-Identifier: Apache-2.0
"""Outcome labels for the trials of a finished `helpdesk_exfil` log (see `label`)."""

from probo.outcomes.label import (
    ERROR_OUTCOMES,
    GENERATE_ERROR_PREFIX,
    REQUIRED_SCORERS,
    TrialKind,
    TrialLabel,
    label_log,
    label_sample,
)

__all__ = [
    "ERROR_OUTCOMES",
    "GENERATE_ERROR_PREFIX",
    "REQUIRED_SCORERS",
    "TrialKind",
    "TrialLabel",
    "label_log",
    "label_sample",
]
