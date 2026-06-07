from datetime import timedelta
from pathlib import Path

import pytest

from rlab.cache.cleanup import clean_cache
from rlab.cache.manager import CacheManager
from rlab.cache.paths import CachePaths
from rlab.data.ablation import DataAblation, DataExperiment
from rlab.data.check import DataCheckResult
from rlab.data.compare import compare_profiles
from rlab.data.diff import diff_records, record_key
from rlab.data.io import read_jsonl, write_jsonl
from rlab.data.pipeline import DataPipeline
from rlab.data.profile import profile_records
from rlab.data.report import data_report
from rlab.data.sample import sample_records
from rlab.reporting.export import export_rows
from rlab.reporting.markdown import markdown_table
from rlab.reporting.plots import line_plot
from rlab.reporting.tables import mapping_table
from rlab.typing import Record


def test_data_helpers(tmp_path: Path) -> None:
    records: tuple[Record, ...] = ({"text": "a", "missing": None}, {"text": "bb"})
    path = tmp_path / "data.jsonl"
    assert write_jsonl(path, records) == 2
    assert tuple(read_jsonl(path)) == records
    profile = profile_records(read_jsonl(path))
    assert profile["records"] == 2
    assert profile["fields"] == {"text": 2, "missing": 1}
    assert sample_records(read_jsonl(path), 1) == (records[0],)
    right: tuple[Record, ...] = (records[1], {"text": "c"})
    result = diff_records(records, right)
    assert result["removed"] == (records[0],)
    assert len(result["added"]) == 1
    assert record_key(records[0])
    compared = compare_profiles({"a": {"records": 1}, "b": {"records": 2}})
    assert compared["records"] == {"a": 1, "b": 2}
    assert "Dataset x" in data_report("x", profile, {"check": "passed"})


def test_data_models() -> None:
    assert DataPipeline(sources=("source",)).outputs["data"] == Path("data.jsonl")
    assert DataCheckResult(success=True).success
    ablation = DataAblation(base="dataset:x", factors={"enabled": [True, False]})
    assert len(ablation.variants()) == 2
    experiment = DataExperiment(question="q", matrix={"dataset": ["x"]})
    assert experiment.question == "q"


@pytest.mark.parametrize("format_name", ["json", "csv", "md", "latex"])
def test_reporting_exports(tmp_path: Path, format_name: str) -> None:
    output = tmp_path / f"report.{format_name}"
    export_rows(({"name": "a", "score": 1},), format_name, output)
    assert output.read_text()
    assert markdown_table(({"name": "a"},)).startswith("| name |")
    assert mapping_table("test", ({"name": "a"},)).title == "test"
    with pytest.raises(ValueError):
        export_rows((), "unknown", output)


def test_plot_and_cache(tmp_path: Path) -> None:
    plot = tmp_path / "plot.svg"
    line_plot((1.0, 2.0), plot)
    assert "<svg" in plot.read_text()
    with pytest.raises(ValueError):
        line_plot((), plot)
    paths = CachePaths(root=tmp_path / "cache")
    assert paths.external.name == "external"
    manager = CacheManager(paths.root)
    file = paths.root / "entry"
    file.write_text("x")
    assert manager.size() == 1
    assert manager.entries() == (file,)
    assert clean_cache(paths.root, timedelta(days=1)) == ()
    assert clean_cache(paths.root) == (file,)
    assert clean_cache(tmp_path / "missing") == ()
