from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path

import pytest

import rlab
from rlab.constants import EntryKind
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.data.context import DataContext
from rlab.data.ids import OutputId
from rlab.data.recipe import FunctionSink
from rlab.data.runner import build_dataset
from rlab.manifests.checksum import sha256
from rlab.manifests.validation import validate_dataset_manifest
from rlab.registry.context import using_registry


def _runtime(tmp_path: Path) -> RuntimeContext:
    (tmp_path / "lab.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return build_runtime(tmp_path)


def _strip(
    records: Iterable[dict[str, object]],
    _ctx: DataContext,
) -> Iterable[dict[str, object]]:
    for record in records:
        yield {**record, "text": str(record["text"]).strip()}


def _nonempty(rows: Sequence[dict[str, object]], _ctx: DataContext) -> rlab.CheckResult:
    return rlab.CheckResult(bool(rows))


def _record_count(rows: Sequence[dict[str, object]], _ctx: DataContext) -> int:
    return len(rows)


def test_typed_recipe_writes_manifest(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    output = tmp_path / "run"

    with using_registry(runtime.registry):

        @rlab.dataset(
            "test.dataset",
            stages=(_strip,),
            checks=(_nonempty,),
            metrics=(_record_count,),
            version="2",
        )
        def source(_ctx: DataContext) -> Iterable[dict[str, object]]:
            yield {"text": " hello "}

    manifest = build_dataset(
        runtime.registry,
        "test.dataset",
        DataContext(runtime=runtime, work_dir=output),
        output,
        version="2",
    )

    assert manifest.inputs == ("source",)
    assert manifest.stages == ("_strip",)
    assert manifest.stats == {"records": 1, "_record_count": 1}
    assert manifest.checks == {"_nonempty": "passed"}
    assert manifest.outputs["data"].path.read_text() == '{"text": "hello"}\n'
    validate_dataset_manifest(manifest)


def test_dataset_rejects_duplicate_stage_names(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with using_registry(runtime.registry):
        with pytest.raises(ValueError, match="duplicate stage"):

            @rlab.dataset("test.dup", stages=(_strip, _strip))
            def source(_ctx: DataContext) -> Iterable[dict[str, object]]:
                yield {}


def test_dataset_rejects_lambda_source(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with using_registry(runtime.registry):
        with pytest.raises(ValueError, match="lambdas are not allowed"):
            rlab.dataset("test.lambda")(lambda ctx: iter([]))  # type: ignore[arg-type]


def test_dataset_rejects_lambda_stage(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    def src(_ctx: DataContext) -> Iterable[dict[str, object]]:
        yield {}

    with using_registry(runtime.registry):
        with pytest.raises(ValueError, match="lambdas are not allowed"):

            @rlab.dataset("test.lambda_stage", stages=(lambda r, c: r,))  # type: ignore[arg-type]
            def _src(_ctx: DataContext) -> Iterable[dict[str, object]]:
                yield {}


def test_runner_rejects_invalid_outputs(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    output = tmp_path / "run"

    for path, error in (
        (Path("missing/data.jsonl"), FileNotFoundError),
        (Path("../outside.jsonl"), ValueError),
    ):

        def invalid_output(
            _rows: Sequence[dict[str, object]],
            ctx: DataContext,
            value: Path = path,
        ) -> rlab.SinkResult:
            return rlab.SinkResult(outputs={OutputId("data"): ctx.work_dir / value})

        runtime.registry.clear()
        with using_registry(runtime.registry):

            @rlab.dataset("test.dataset", sinks=(FunctionSink(OutputId("data"), invalid_output),))
            def source(_ctx: DataContext) -> Iterable[dict[str, object]]:
                yield {}

        with pytest.raises(error):
            build_dataset(
                runtime.registry,
                "test.dataset",
                DataContext(runtime=runtime, work_dir=output),
                output,
            )


def test_dataset_registers_only_dataset_entries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    with using_registry(runtime.registry):

        @rlab.dataset("test.only")
        def source(_ctx: DataContext) -> Iterable[dict[str, object]]:
            yield {}

    assert [record.kind for record in runtime.registry.list()] == [EntryKind.DATASET]


def test_old_data_api_is_removed() -> None:
    for name in (
        "DataFlow",
        "DatasetRecipe",
        "DatasetCatalog",
        "FunctionSource",
        "FunctionStage",
        "FunctionCheck",
        "FunctionMetric",
        "FunctionSink",
        "register_datasets",
        "DatasetId",
        "StageId",
        "CheckId",
        "MetricId",
    ):
        assert not hasattr(rlab, name), f"rlab.{name} should not be in the public API"


def test_directory_checksum_includes_relative_paths(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "a.txt").write_text("same", encoding="utf-8")
    (right / "b.txt").write_text("same", encoding="utf-8")
    assert sha256(left) != sha256(right)
