from __future__ import annotations

from pathlib import Path

import pytest

from rlab.constants import RunStatus
from rlab.context.runtime import RuntimeContext
from rlab.runs.layout import RunLayout
from rlab.runs.reader import RunReader
from rlab.runs.writer import RunWriter


def test_run_layout_writer_and_reader_round_trip(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run_001")
    writer = RunWriter(layout)
    writer.status(RunStatus.RUNNING)
    writer.metric("accuracy", 0.92, unit="percentage")
    writer.metric("loss", 0.3)
    writer.params({"lr": 0.001, "batch_size": 32})
    writer.note("Something interesting happened")
    writer.table("results", [{"col1": 1, "col2": "a"}], fmt="csv")
    writer.status(RunStatus.COMPLETED)

    reader = RunReader(layout.root)
    assert reader.status() == RunStatus.COMPLETED
    assert reader.params()["lr"] == pytest.approx(0.001)
    assert any(record["name"] == "accuracy" for record in reader.metrics())
    assert reader.notes()[0]["text"] == "Something interesting happened"
    assert (layout.tables / "results.csv").exists()


def test_runtime_context_writes_into_active_run(runtime: RuntimeContext, tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run_ctx")
    layout.create()
    ctx = runtime.model_copy(update={"run_dir": layout.root})

    ctx.log_metric("loss", 0.5, unit="dimensionless")
    ctx.note("Important observation")
    ctx.save_table("records", [{"value": 1}])

    reader = RunReader(layout.root)
    assert reader.metrics()[0]["name"] == "loss"
    assert len(reader.notes()) == 1
    assert (layout.tables / "records.csv").exists()


def test_metric_summary_keeps_latest_value(tmp_path: Path) -> None:
    layout = RunLayout(root=tmp_path / "run_001")
    writer = RunWriter(layout)
    writer.metric("val_loss", 0.45)
    writer.metric("val_loss", 0.40)

    assert RunReader(layout.root).metrics_summary()["val_loss"] == pytest.approx(0.40)
