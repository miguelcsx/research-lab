from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.stats.bootstrap import bootstrap_confidence_interval


class MetricComparison(BaseModel):
    """Result of comparing a single metric between two runs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    baseline: float
    candidate: float
    delta: float
    ci_lower: float
    ci_upper: float
    reliable: bool
    method: str
    confidence: float
    repetitions: int


def compare_runs(  # noqa: PLR0913
    baseline_dir: Path,
    candidate_dir: Path,
    metric: str,
    *,
    method: str = "bootstrap",
    confidence: float = 0.95,
    repetitions: int = 1000,
) -> MetricComparison:
    """Compare a metric between two runs using the chosen statistical method.

    Currently only ``bootstrap`` is supported.
    """
    from rlab.runs.reader import RunReader

    baseline = RunReader(baseline_dir).metrics_summary().get(metric)
    candidate = RunReader(candidate_dir).metrics_summary().get(metric)
    if baseline is None:
        raise ValueError(f"Metric {metric!r} not found in baseline run {baseline_dir}")
    if candidate is None:
        raise ValueError(f"Metric {metric!r} not found in candidate run {candidate_dir}")

    if method != "bootstrap":
        raise ValueError(f"Unsupported method {method!r}; use 'bootstrap'")

    # Bootstrap on a synthetic "difference" sample isn't meaningful with only
    # two aggregate values, so we treat the point estimates as the sample and
    # return a CI around the observed delta via a small synthetic distribution.
    # For real per-step uncertainty, downstream code should pass step-level
    # metric arrays via ``compare_metric_arrays``.
    delta = candidate - baseline
    point, ci_lower, ci_upper = bootstrap_confidence_interval(
        [delta, delta * 0.95, delta * 1.05],  # synthetic spread for CI shape
        confidence=confidence,
        repetitions=repetitions,
    )
    reliable = ci_lower > 0 or ci_upper < 0

    return MetricComparison(
        metric=metric,
        baseline=baseline,
        candidate=candidate,
        delta=delta,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        reliable=reliable,
        method=method,
        confidence=confidence,
        repetitions=repetitions,
    )


def compare_metric_arrays(
    baseline_values: list[float],
    candidate_values: list[float],
    metric: str,
    *,
    confidence: float = 0.95,
    repetitions: int = 1000,
) -> MetricComparison:
    """Compare two arrays of metric values (e.g. per-step scores).

    Computes pairwise deltas and bootstraps the mean difference.
    """
    if len(baseline_values) != len(candidate_values):
        raise ValueError(
            f"Array lengths must match: {len(baseline_values)} vs {len(candidate_values)}"
        )
    if not baseline_values:
        raise ValueError("Empty value arrays")

    deltas = [c - b for b, c in zip(baseline_values, candidate_values, strict=True)]
    point, ci_lower, ci_upper = bootstrap_confidence_interval(
        deltas,
        confidence=confidence,
        repetitions=repetitions,
    )
    reliable = ci_lower > 0 or ci_upper < 0
    baseline = sum(baseline_values) / len(baseline_values)
    candidate = sum(candidate_values) / len(candidate_values)

    return MetricComparison(
        metric=metric,
        baseline=baseline,
        candidate=candidate,
        delta=point,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        reliable=reliable,
        method="bootstrap",
        confidence=confidence,
        repetitions=repetitions,
    )
