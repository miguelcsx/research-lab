from collections.abc import Iterable
from pathlib import Path
from typing import Any

from rlab.runs.reader import RunReader


def compare_runs(paths: Iterable[Path]) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        reader = RunReader(path)
        manifest = reader.manifest()
        results = reader.results()
        metrics = {
            metric["name"]: metric["value"]
            for metric in reader.metrics()
            if "name" in metric and "value" in metric
        }
        rows.append(
            {
                "run": path.name,
                "operation": manifest.operation,
                **manifest.parameters,
                **metrics,
                "result": results,
            }
        )
    return tuple(rows)
