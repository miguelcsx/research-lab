from __future__ import annotations

from pathlib import Path

import pytest

from rlab.constants import EntryKind
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.data.context import DataContext
from rlab.data.pipeline import DataBuildResult, DataPipeline
from rlab.data.runner import build_dataset
from rlab.manifests.checksum import sha256
from rlab.manifests.validation import validate_dataset_manifest
from rlab.registry.decorators import register


def _runtime(tmp_path: Path) -> RuntimeContext:
    (tmp_path / "lab.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return build_runtime(tmp_path)


def test_custom_builder_writes_multi_output_manifest(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)

    def builder(ctx: DataContext) -> DataBuildResult:
        data = ctx.work_dir / "data.jsonl"
        bundle = ctx.work_dir / "bundle"
        data.parent.mkdir(parents=True)
        data.write_text('{"text": "hello"}\n', encoding="utf-8")
        bundle.mkdir()
        (bundle / "metadata.json").write_text("{}", encoding="utf-8")
        return DataBuildResult(
            outputs={"data": data, "bundle": bundle},
            stats={"records": 1},
            checks={"budget": "passed"},
            licenses=("test-license",),
        )

    def dataset() -> DataPipeline:
        return DataPipeline(builder="test.builder", params={"limit": 1})

    register(runtime.registry, EntryKind.DATA_BUILDER, "test.builder", builder)
    register(runtime.registry, EntryKind.DATASET, "test.dataset", dataset)
    output = tmp_path / "run"
    manifest = build_dataset(
        runtime.registry,
        "test.dataset",
        DataContext(runtime=runtime, work_dir=output),
        output,
    )

    assert manifest.stats == {"records": 1}
    assert manifest.checks == {"budget": "passed"}
    assert manifest.licenses == ("test-license",)
    assert manifest.outputs["bundle"].is_directory
    assert manifest.outputs["bundle"].size_bytes == 2
    validate_dataset_manifest(manifest)


def test_custom_builder_rejects_invalid_outputs(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    output = tmp_path / "run"

    def dataset() -> DataPipeline:
        return DataPipeline(builder="test.builder")

    register(runtime.registry, EntryKind.DATASET, "test.dataset", dataset)

    for result, error in (
        (DataBuildResult(outputs={}), ValueError),
        (DataBuildResult(outputs={"data": output / "missing"}), FileNotFoundError),
        (DataBuildResult(outputs={"data": tmp_path / "outside"}), ValueError),
    ):
        register(
            runtime.registry,
            EntryKind.DATA_BUILDER,
            "test.builder",
            lambda _ctx, value=result: value,
        )
        with pytest.raises(error):
            build_dataset(
                runtime.registry,
                "test.dataset",
                DataContext(runtime=runtime, work_dir=output),
                output,
            )
        runtime.registry.clear()
        register(runtime.registry, EntryKind.DATASET, "test.dataset", dataset)


def test_directory_checksum_includes_relative_paths(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    left.mkdir()
    right.mkdir()
    (left / "a.txt").write_text("same", encoding="utf-8")
    (right / "b.txt").write_text("same", encoding="utf-8")

    assert sha256(left) != sha256(right)


def test_pipeline_requires_one_execution_mode() -> None:
    with pytest.raises(ValueError, match="requires sources or a builder"):
        DataPipeline()
    with pytest.raises(ValueError, match="cannot declare record stages"):
        DataPipeline(builder="test.builder", sources=("test.source",))
