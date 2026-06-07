import json
from pathlib import Path

REQUIRED_RUN_FILES = (
    "run.yaml",
    "metrics.jsonl",
    "results.json",
    "report.md",
    "command.txt",
    "git.json",
    "env.json",
)


def assert_valid_run_dir(path: Path) -> None:
    missing = [name for name in REQUIRED_RUN_FILES if not (path / name).exists()]
    if missing:
        raise AssertionError(f"Missing run files: {', '.join(missing)}")


def assert_metric_exists(path: Path, name: str) -> None:
    metrics = [json.loads(line) for line in (path / "metrics.jsonl").read_text().splitlines()]
    if not any(metric["name"] == name for metric in metrics):
        raise AssertionError(f"Metric {name!r} was not found")
