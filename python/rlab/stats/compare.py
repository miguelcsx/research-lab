"""Small Python convenience layer for metric comparisons."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from statistics import mean


@dataclass(slots=True)
class MetricComparison:
    mean_a: float
    mean_b: float
    delta: float
    effect_size: float | None = None
    confidence_interval: tuple[float, float] | None = None


def compare_metric_arrays(a: list[float], b: list[float]) -> MetricComparison:
    if not a or not b:
        raise ValueError("metric arrays must be non-empty")
    mean_a = float(mean(a))
    mean_b = float(mean(b))
    return MetricComparison(
        mean_a=mean_a,
        mean_b=mean_b,
        delta=mean_b - mean_a,
        effect_size=_standardized_effect(a, b),
    )


def paired_bootstrap(
    a: list[float],
    b: list[float],
    *,
    samples: int = 10_000,
    confidence: float = 0.95,
    seed: int = 0,
) -> MetricComparison:
    if len(a) != len(b) or not a:
        raise ValueError("paired arrays must be non-empty and equal length")
    if samples < 1 or not 0.0 < confidence < 1.0:
        raise ValueError("invalid bootstrap configuration")
    rng = random.Random(seed)
    differences = [right - left for left, right in zip(a, b, strict=True)]
    estimates = sorted(
        mean(differences[rng.randrange(len(differences))] for _ in differences)
        for _ in range(samples)
    )
    tail = (1.0 - confidence) / 2.0
    lower = estimates[min(int(tail * samples), samples - 1)]
    upper = estimates[min(int((1.0 - tail) * samples), samples - 1)]
    comparison = compare_metric_arrays(a, b)
    return MetricComparison(
        comparison.mean_a,
        comparison.mean_b,
        comparison.delta,
        comparison.effect_size,
        (float(lower), float(upper)),
    )


def _standardized_effect(a: list[float], b: list[float]) -> float | None:
    differences = [right - left for left, right in zip(a, b, strict=False)]
    if len(differences) < 2:
        return None
    center = mean(differences)
    variance = sum((value - center) ** 2 for value in differences) / (
        len(differences) - 1
    )
    deviation = math.sqrt(variance)
    return None if deviation == 0.0 else float(center / deviation)
