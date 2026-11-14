# SPDX-License-Identifier: Apache-2.0
"""Statistics for Probo results: Wilson intervals, labelled rates and judge confusion matrices.

Every rate is published with its trial count, its Wilson interval and what it estimates.
"""

from probo.stats.attack import AttackSuccess, OutcomeCounts
from probo.stats.confusion import ConfusionMatrix
from probo.stats.rate import Estimand, Proportion, Rate
from probo.stats.wilson import Interval, wilson_interval

__all__ = [
    "AttackSuccess",
    "ConfusionMatrix",
    "Estimand",
    "Interval",
    "OutcomeCounts",
    "Proportion",
    "Rate",
    "wilson_interval",
]
