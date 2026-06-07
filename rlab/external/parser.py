import json
from collections.abc import Callable
from pathlib import Path

ResultParser = Callable[[Path], dict[str, float]]


def json_metrics(path: Path) -> dict[str, float]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    metrics = {
        str(name): float(value)
        for name, value in data.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    if not metrics:
        raise ValueError(f"No numeric metrics in {path}")
    return metrics
