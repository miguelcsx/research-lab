from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from rlab.cache.cleanup import clean_cache
from rlab.cache.manager import CacheManager
from rlab.cache.paths import CachePaths
from rlab.data.ablation import DataAblation, DataExperiment
from rlab.data.compare import compare_profiles
from rlab.data.diff import diff_records, record_key
from rlab.data.ids import OutputId
from rlab.data.io import read_jsonl, write_jsonl
from rlab.data.model import CheckResult
from rlab.data.profile import profile_records
from rlab.data.report import data_report
from rlab.data.sample import sample_records
from rlab.data.sinks import JsonlSink
from rlab.reporting.export import export_rows
from rlab.reporting.markdown import markdown_table
from rlab.reporting.plots import line_plot
from rlab.reporting.tables import mapping_table
from rlab.typing import Record


def test_data_io_profile_sample_diff_and_report(tmp_path: Path) -> None:
    records: tuple[Record, ...] = ({"text": "a", "missing": None}, {"text": "bb"})
    path = tmp_path / "data.jsonl"
    assert write_jsonl(path, records) == 2
    assert tuple(read_jsonl(path)) == records

    profile = profile_records(read_jsonl(path))
    assert profile["records"] == 2
    assert profile["fields"] == {"text": 2, "missing": 1}
    assert sample_records(read_jsonl(path), 1) == (records[0],)
    assert record_key(records[0])
    assert diff_records(records, (records[1], {"text": "c"}))["removed"] == (records[0],)
    assert compare_profiles({"a": {"records": 1}, "b": {"records": 2}})["records"] == {
        "a": 1,
        "b": 2,
    }
    assert "Dataset x" in data_report("x", profile, {"check": "passed"})


def test_data_models() -> None:
    assert JsonlSink().id == OutputId("data")
    assert JsonlSink().path == Path("data.jsonl")
    assert CheckResult(passed=True).passed
    assert len(DataAblation(base="dataset:x", factors={"enabled": [True, False]}).variants()) == 2
    assert DataExperiment(question="q", matrix={"dataset": ["x"]}).question == "q"


@pytest.mark.parametrize("format_name", ["json", "csv", "md", "latex"])
def test_reporting_exports(tmp_path: Path, format_name: str) -> None:
    output = tmp_path / f"report.{format_name}"
    export_rows(({"name": "a", "score": 1},), format_name, output)
    assert output.read_text(encoding="utf-8")
    assert markdown_table(({"name": "a"},)).startswith("| name |")
    assert mapping_table("test", ({"name": "a"},)).title == "test"


def test_reporting_rejects_unknown_export_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        export_rows((), "unknown", tmp_path / "report.txt")


def test_plot_and_cache(tmp_path: Path) -> None:
    plot = tmp_path / "plot.svg"
    line_plot((1.0, 2.0), plot)
    assert "<svg" in plot.read_text(encoding="utf-8")
    with pytest.raises(ValueError):
        line_plot((), plot)

    paths = CachePaths(root=tmp_path / "cache")
    manager = CacheManager(paths.root)
    file = paths.root / "entry"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text("x", encoding="utf-8")

    assert paths.external.name == "external"
    assert manager.size() == 1
    assert manager.entries() == (file,)
    assert clean_cache(paths.root, timedelta(days=1)) == ()
    assert clean_cache(paths.root) == (file,)
    assert clean_cache(tmp_path / "missing") == ()
