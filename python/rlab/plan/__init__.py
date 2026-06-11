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
    _validate_power_inputs(
        effect_size=effect_size,
        variance=variance,
        alpha=alpha,
        power=power,
    )

    return max(
        1, math.ceil(_required_repetitions_value(effect_size, variance, alpha, power))
    )


def estimate_budget(
    jobs: int, seconds_per_job: float, storage_gb_per_job: float
) -> BudgetEstimate:
    _validate_budget_inputs(
        jobs=jobs,
        seconds_per_job=seconds_per_job,
        storage_gb_per_job=storage_gb_per_job,
    )

    return BudgetEstimate(
        jobs=jobs,
        total_seconds=_total_resource(jobs, seconds_per_job),
        total_storage_gb=_total_resource(jobs, storage_gb_per_job),
    )


def _validate_power_inputs(
    *,
    effect_size: float,
    variance: float,
    alpha: float,
    power: float,
) -> None:
    if (
        effect_size <= 0
        or variance < 0
        or not _is_probability(alpha)
        or not _is_probability(power)
    ):
        raise ValueError("invalid power planning inputs")


def _validate_budget_inputs(
    *,
    jobs: int,
    seconds_per_job: float,
    storage_gb_per_job: float,
) -> None:
    if jobs < 0 or seconds_per_job < 0 or storage_gb_per_job < 0:
        raise ValueError("budget inputs must be non-negative")


def _is_probability(value: float) -> bool:
    return 0 < value < 1


def _required_repetitions_value(
    effect_size: float,
    variance: float,
    alpha: float,
    power: float,
) -> float:
    return variance * _power_penalty(alpha, power) / _squared(effect_size)


def _power_penalty(alpha: float, power: float) -> float:
    return 1.0 / alpha + 1.0 / (1.0 - power)


def _squared(value: float) -> float:
    return value * value


def _total_resource(jobs: int, resource_per_job: float) -> float:
    return jobs * resource_per_job


__all__ = ["BudgetEstimate", "estimate_budget", "estimate_required_repetitions"]
