from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

import rlab
from rlab.constants import EntryKind
from rlab.context.factory import build_runtime
from rlab.context.runtime import RuntimeContext
from rlab.data.context import DataContext
from rlab.data.runner import build_dataset
from rlab.data.sinks import register_builtin_sinks
from rlab.manifests.validation import validate_dataset_manifest
from rlab.typing import JsonValue

Record = dict[str, JsonValue]


def _runtime(tmp_path: Path) -> RuntimeContext:
    (tmp_path / "lab.toml").write_text("[project]\nname = 'test'\n", encoding="utf-8")
    return build_runtime(tmp_path)


def _declare_pipeline(runtime: RuntimeContext, *, audit: rlab.AuditPolicy | None = None) -> None:
    lab = rlab.Project("data-builders-test", root=runtime.paths.root)
    # Point the runtime at the project's registry so downstream lookups work.
    runtime.registry = lab.registry
    # The built-in sinks live in the registry that ``build_runtime`` set up.
    # Re-register them on the new (Project) registry so dataset runs can find
    # e.g. ``sink:rlab.jsonl``.
    register_builtin_sinks(runtime.registry)

    @lab.source("test.source", version="1.1.0")
    @dataclass(frozen=True, slots=True)
    class Source:
        limit: int = 2

        def read(self, _ctx: DataContext) -> Iterable[Record]:
            yield from ({"text": " hello "}, {"text": ""})[: self.limit]

    @lab.transform("test.strip", version="2.0.0")
    @dataclass(frozen=True, slots=True)
    class Strip:
        def apply(self, record: Record, _ctx: DataContext) -> rlab.Decision[Record]:
            text = str(record["text"]).strip()
            if not text:
                return rlab.drop("empty")
            return rlab.update({**record, "text": text}, reason="stripped")

    @lab.check("test.nonempty")
    @dataclass(frozen=True, slots=True)
    class Nonempty:
        def evaluate(self, records: Sequence[Record], _ctx: DataContext) -> rlab.CheckResult:
            return rlab.CheckResult(bool(records))

    @lab.metric("test.record_count")
    @dataclass(frozen=True, slots=True)
    class RecordCount:
        def measure(self, records: Sequence[Record], _ctx: DataContext) -> JsonValue:
            return len(records)

    test_pipeline = lab.pipeline(
        "test.pipeline",
        rlab.ComponentUse("transform:test.strip"),
        version="3.0.0",
    )

    lab.dataset(
        "test.dataset",
        source=rlab.ComponentUse("source:test.source"),
        pipeline=test_pipeline,
        sinks=(rlab.ComponentUse("sink:rlab.jsonl"),),
        checks=(rlab.ComponentUse("check:test.nonempty"),),
        metrics=(rlab.ComponentUse("metric:test.record_count"),),
        audit=audit,
        version="4.0.0",
    )


def test_declarative_dataset_writes_versioned_manifest_and_audit(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    output = tmp_path / "run"
    _declare_pipeline(
        runtime,
        audit=rlab.AuditPolicy(capture_decisions=True, sample_reasons={"empty": 1}),
    )

    manifest = build_dataset(
        runtime.registry,
        "test.dataset",
        DataContext(runtime=runtime, work_dir=output),
        output,
    )

    assert manifest.version == "4.0.0"
    assert manifest.declaration == "dataset:test.dataset@4.0.0"
    assert manifest.pipeline == "pipeline:test.pipeline@3.0.0"
    assert manifest.inputs == ("source:test.source@1.1.0",)
    assert manifest.stages == ("transform:test.strip@2.0.0",)
    assert manifest.stats["records"] == 1
    assert manifest.stats["metric:test.record_count@1.0.0"] == 1
    assert manifest.checks["check:test.nonempty@1.0.0"] == "passed"
    assert manifest.outputs["data"].path.read_text() == '{"text": "hello"}\n'
    assert manifest.audit.summary.exists()
    assert manifest.audit.decisions is not None and manifest.audit.decisions.exists()
    assert manifest.audit.samples["empty"].exists()
    assert set(manifest.audit.samples) == {"empty"}
    validate_dataset_manifest(manifest)


def test_typed_source_override_is_validated(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _declare_pipeline(runtime)

    manifest = build_dataset(
        runtime.registry,
        "test.dataset",
        DataContext(runtime=runtime, work_dir=tmp_path / "valid"),
        tmp_path / "valid",
        overrides={"source.limit": 1},
    )
    assert manifest.stats["records"] == 1
    assert manifest.configuration["source:test.source@1.1.0"] == {"limit": 1}

    with pytest.raises(Exception, match="Invalid configuration"):
        build_dataset(
            runtime.registry,
            "test.dataset",
            DataContext(runtime=runtime, work_dir=tmp_path / "invalid"),
            tmp_path / "invalid",
            overrides={"source.limit": "wrong"},
        )


def test_boundaries_bypass_record_stages_and_must_be_consumed(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lab = rlab.Project("boundaries", root=runtime.paths.root)
    runtime.registry = lab.registry

    @lab.source("test.boundaries")
    @dataclass(frozen=True, slots=True)
    class Source:
        def read(self, _ctx: DataContext) -> Iterable[Record]:
            yield {"text": "break"}
            yield {"text": "value"}

    @lab.transform("test.boundary")
    @dataclass(frozen=True, slots=True)
    class BoundaryTransform:
        def apply(self, record: Record, _ctx: DataContext) -> rlab.Decision[Record]:
            if record["text"] == "break":
                return rlab.boundary("document")
            return rlab.keep(record)

    @lab.filter("test.must_not_see_boundary")
    @dataclass(frozen=True, slots=True)
    class Filter:
        def apply(self, record: Record, _ctx: DataContext) -> rlab.Decision[Record]:
            return rlab.keep(record)

    boundary_pipeline = lab.pipeline(
        "test.boundary_pipeline",
        rlab.ComponentUse("transform:test.boundary"),
        rlab.ComponentUse("filter:test.must_not_see_boundary"),
    )

    lab.dataset(
        "test.boundary_dataset",
        source=rlab.ComponentUse("source:test.boundaries"),
        pipeline=boundary_pipeline,
        sinks=(rlab.ComponentUse("sink:rlab.jsonl"),),
    )

    with pytest.raises(ValueError, match="unconsumed boundaries"):
        build_dataset(
            runtime.registry,
            "test.boundary_dataset",
            DataContext(runtime=runtime, work_dir=tmp_path / "output"),
            tmp_path / "output",
        )


def test_declarations_require_dataclasses_and_semver(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    lab = rlab.Project("semver", root=runtime.paths.root)
    runtime.registry = lab.registry

    with pytest.raises(TypeError, match="requires a dataclass"):

        @lab.source("test.invalid")
        class Invalid:
            pass

    with pytest.raises(Exception, match="semantic version"):
        lab.pipeline("test.invalid", version="1")


def test_dataset_registers_semantic_entries(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    _declare_pipeline(runtime)
    kinds = {record.kind for record in runtime.registry.list()}
    assert EntryKind.DATASET in kinds
    assert EntryKind.PIPELINE in kinds
    assert EntryKind.SOURCE in kinds
    assert EntryKind.TRANSFORM in kinds
