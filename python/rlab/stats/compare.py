"""Small Python convenience layer for metric comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(slots=True)
class MetricComparison:
    mean_a: float
    mean_b: float
    delta: float


def compare_metric_arrays(a: list[float], b: list[float]) -> MetricComparison:
    if not a or not b:
        raise ValueError("metric arrays must be non-empty")
    mean_a = float(mean(a))
    mean_b = float(mean(b))
    return MetricComparison(mean_a=mean_a, mean_b=mean_b, delta=mean_b - mean_a)
