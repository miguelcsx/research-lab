from __future__ import annotations

import json
from pathlib import Path

from rlab import RunRef


def test_runner_no_longer_exposes_python_child_run_wrapper() -> None:
    import rlab._runner as runner

    assert not hasattr(runner, "_ChildContext")
    assert not hasattr(runner, "_child_command")
    assert not hasattr(runner, "_run_data")


def test_run_ref_resolves_named_artifacts(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    (artifact_dir / "artifacts.jsonl").write_text(
        json.dumps(
            {
                "name": "encoded.train",
                "kind": "directory",
                "path": str(tmp_path / "outputs" / "encoded" / "train"),
                "staged_path": str(tmp_path / "artifacts" / "directory" / "encoded.train"),
            }
        )
        + "\n",
        encoding="utf-8",
    )

    ref = RunRef("run", "workflow:encode", tmp_path).artifact("encoded.train")

    assert ref.kind == "directory"
    assert ref.path == tmp_path / "artifacts" / "directory" / "encoded.train"


def test_run_ref_reads_metric_summary(tmp_path: Path) -> None:
    (tmp_path / "metrics_summary.json").write_text(
        json.dumps({"validation.loss": 1.25}),
        encoding="utf-8",
    )

    assert RunRef("run", "experiment:x", tmp_path).metric("validation.loss") == 1.25

