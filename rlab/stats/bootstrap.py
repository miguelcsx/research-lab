from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TypeVar

T = TypeVar("T", float, int)


def bootstrap_confidence_interval(
    values: Sequence[float],
    *,
    statistic: str = "mean",
    confidence: float = 0.95,
    repetitions: int = 1000,
    seed: int = 0,
) -> tuple[float, float, float]:
    """Return (point_estimate, lower, upper) via percentile bootstrap.

    Args:
        values: Numeric sample.
        statistic: "mean" or "median".
        confidence: Two-sided confidence level (e.g. 0.95).
        repetitions: Number of bootstrap resamples.
        seed: Random seed for reproducibility.

    Returns:
        (point_estimate, ci_lower, ci_upper)
    """
    if not values:
        return (0.0, 0.0, 0.0)

    rng = random.Random(seed)
    n = len(values)
    point = _point_estimate(values, statistic)

    replicates: list[float] = []
    for _ in range(repetitions):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        replicates.append(_point_estimate(sample, statistic))

    replicates.sort()
    alpha = 1.0 - confidence
    lower_idx = int(alpha / 2 * repetitions)
    upper_idx = int((1.0 - alpha / 2) * repetitions)
    lower_idx = max(0, min(lower_idx, repetitions - 1))
    upper_idx = max(0, min(upper_idx, repetitions - 1))
    return (point, replicates[lower_idx], replicates[upper_idx])


def _point_estimate(values: Sequence[float], statistic: str) -> float:
    if statistic == "median":
        s = sorted(values)
        n = len(s)
        if n % 2:
            return float(s[n // 2])
        return (s[n // 2 - 1] + s[n // 2]) / 2.0
    return sum(values) / len(values)
