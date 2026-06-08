from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

_EPS = 1e-9


class CategoryRegression(BaseModel):
    """Change in a metric for one category between two runs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    category: str
    baseline: float
    candidate: float
    delta: float


class ErrorComparison(BaseModel):
    """Result of comparing per-example or per-category errors between runs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str
    by: str
    regressions: tuple[CategoryRegression, ...]
    improvements: tuple[CategoryRegression, ...]
    unchanged: tuple[CategoryRegression, ...]


def compare_runs_errors(
    baseline_dir: Path,
    candidate_dir: Path,
    *,
    metric: str,
    by: str = "category",
) -> ErrorComparison:
    """Compare per-example or per-category metric values between two runs.

    Reads ``results.json`` from each run and expects a ``records`` field
    where each record has at least ``{by}`` and ``{metric}`` keys.

    Returns regressions, improvements, and unchanged categories sorted
    by absolute delta.
    """
    from rlab.runs.reader import RunReader

    baseline_records = _load_records(RunReader(baseline_dir))
    candidate_records = _load_records(RunReader(candidate_dir))

    baseline_by = _group(baseline_records, by, metric)
    candidate_by = _group(candidate_records, by, metric)

    categories = sorted(set(baseline_by.keys()) | set(candidate_by.keys()))
    regressions: list[CategoryRegression] = []
    improvements: list[CategoryRegression] = []
    unchanged: list[CategoryRegression] = []

    for cat in categories:
        b = baseline_by.get(cat, 0.0)
        c = candidate_by.get(cat, 0.0)
        delta = c - b
        item = CategoryRegression(category=cat, baseline=b, candidate=c, delta=delta)
        if delta > _EPS:
            improvements.append(item)
        elif delta < -_EPS:
            regressions.append(item)
        else:
            unchanged.append(item)

    regressions.sort(key=lambda x: abs(x.delta), reverse=True)
    improvements.sort(key=lambda x: abs(x.delta), reverse=True)

    return ErrorComparison(
        metric=metric,
        by=by,
        regressions=tuple(regressions),
        improvements=tuple(improvements),
        unchanged=tuple(unchanged),
    )


def _load_records(reader: Any) -> list[dict[str, Any]]:
    results = reader.results()
    records = results.get("records")
    if isinstance(records, list):
        return records
    # Fallback: look for steps with per-step metrics as dicts
    steps = results.get("steps", ())
    out: list[dict[str, Any]] = []
    for step in steps:
        metrics = step.get("metrics")
        if isinstance(metrics, dict):
            out.append(metrics)
    return out


def _group(records: list[dict[str, Any]], by: str, metric: str) -> dict[str, float]:
    """Group records by ``by`` key and average ``metric``."""
    groups: dict[str, list[float]] = defaultdict(list)
    for record in records:
        key = str(record.get(by, "unknown"))
        value = record.get(metric)
        if isinstance(value, (int, float)):
            groups[key].append(float(value))
    return {k: sum(v) / len(v) for k, v in groups.items()}
