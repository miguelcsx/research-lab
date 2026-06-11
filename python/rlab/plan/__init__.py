"""Power and budget helpers."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BudgetEstimate:
    jobs: int
    total_seconds: float
    total_storage_gb: float


def estimate_required_repetitions(
    effect_size: float, variance: float, alpha: float, power: float
) -> int:
    if effect_size <= 0 or variance < 0 or not (0 < alpha < 1) or not (0 < power < 1):
        raise ValueError("invalid power planning inputs")
    return max(
        1,
        math.ceil(
            (variance * (1.0 / alpha + 1.0 / (1.0 - power)))
            / (effect_size * effect_size)
        ),
    )


def estimate_budget(
    jobs: int, seconds_per_job: float, storage_gb_per_job: float
) -> BudgetEstimate:
    if jobs < 0 or seconds_per_job < 0 or storage_gb_per_job < 0:
        raise ValueError("budget inputs must be non-negative")
    return BudgetEstimate(
        jobs=jobs,
        total_seconds=jobs * seconds_per_job,
        total_storage_gb=jobs * storage_gb_per_job,
    )


__all__ = ["BudgetEstimate", "estimate_budget", "estimate_required_repetitions"]
