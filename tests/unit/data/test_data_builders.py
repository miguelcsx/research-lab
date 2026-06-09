from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

import rlab
from rlab.constants import EntryKind
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.data.context import DataContext
from rlab.data.runner import build_dataset
from rlab.manifests.checksum import sha256
from rlab.manifests.validation import validate_dataset_manifest
from rlab.registry.context import using_registry


def _runtime(tmp_path: Path) -> RuntimeContext:
    (tmp_path / "lab.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return build_runtime(tmp_path)


def _source(_ctx: DataContext) -> Iterable[dict[str, object]]:
    yield {"text": " hello "}


def _strip(
    records: Iterable[dict[str, object]],
    _ctx: DataContext,
) -> Iterable[dict[str, object]]:
    for record in records:
        yield {**record, "text": str(record["text"]).strip()}


def _recipe(output: Path = Path("data.jsonl")) -> rlab.DatasetRecipe[dict[str, object]]:
    flow = rlab.DataFlow.from_source(
        rlab.FunctionSource(rlab.SourceId("test.raw"), _source)
    ).then(rlab.FunctionStage(rlab.StageId("test.strip"), _strip))
    return rlab.DatasetRecipe(
        id=rlab.DatasetId("test.dataset"),
        flow=flow,
        sinks=(rlab.JsonlSink(path=output),),
        checks=(
            rlab.FunctionCheck(
                rlab.CheckId("test.nonempty"),
                lambda rows, _ctx: rlab.CheckResult(bool(rows)),
            ),
        ),
        metrics=(
            rlab.FunctionMetric(
                rlab.MetricId("test.records"),
                lambda rows, _ctx: len(rows),
            ),
        ),
        version="2",
    )


def test_typed_recipe_writes_manifest(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with using_registry(runtime.registry):
        rlab.register_datasets(rlab.DatasetCatalog(_recipe()))
    output = tmp_path / "run"
    manifest = build_dataset(
        runtime.registry,
        "test.dataset",
        DataContext(runtime=runtime, work_dir=output),
        output,
        version="2",
    )

    assert manifest.inputs == ("test.raw",)
    assert manifest.stages == ("test.strip",)
    assert manifest.stats == {"records": 1, "test.records": 1}
    assert manifest.checks == {"test.nonempty": "passed"}
    assert manifest.outputs["data"].path.read_text() == '{"text": "hello"}\n'
    validate_dataset_manifest(manifest)


def test_recipe_rejects_duplicate_ids() -> None:
    source = rlab.FunctionSource(rlab.SourceId("same"), _source)
    with pytest.raises(ValueError, match="duplicate source"):
        rlab.DataFlow.from_sources(source, source)


def test_runner_rejects_invalid_outputs(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    output = tmp_path / "run"
    for path, error in (
        (Path("missing/data.jsonl"), FileNotFoundError),
        (Path("../outside.jsonl"), ValueError),
    ):
        def invalid_output(
            _rows: Sequence[dict[str, object]],
            ctx: rlab.DataContext,
            value: Path = path,
        ) -> rlab.SinkResult:
            return rlab.SinkResult(
                outputs={rlab.OutputId("data"): ctx.work_dir / value}
            )

        sink = rlab.FunctionSink[dict[str, object]](
            rlab.OutputId("data"),
            invalid_output,
        )
        recipe = _recipe().replace(sinks=(sink,))
        runtime.registry.clear()
        with using_registry(runtime.registry):
            rlab.register_datasets(rlab.DatasetCatalog(recipe))
        with pytest.raises(error):
            build_dataset(
                runtime.registry,
                "test.dataset",
                DataContext(runtime=runtime, work_dir=output),
                output,
            )


def test_catalog_registers_only_dataset_entries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with using_registry(runtime.registry):
        rlab.register_datasets(rlab.DatasetCatalog(_recipe()))
    assert [record.kind for record in runtime.registry.list()] == [EntryKind.DATASET]


def test_legacy_data_api_is_removed() -> None:
    for name in (
        "DataPipeline",
        "data_source",
        "data_transform",
        "data_builder",
        "dataset_variant",
    ):
        assert not hasattr(rlab, name)


def test_directory_checksum_includes_relative_paths(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "a.txt").write_text("same", encoding="utf-8")
    (right / "b.txt").write_text("same", encoding="utf-8")
    assert sha256(left) != sha256(right)
