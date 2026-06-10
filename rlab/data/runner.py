from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from rlab.constants import EntryKind
from rlab.data.audit import AuditRecorder
from rlab.data.components import (
    apply_dataset_overrides,
    canonical_component,
    component_configuration,
    instantiate_component,
)
from rlab.data.context import DataContext
from rlab.data.manifest import dataset_manifest
from rlab.data.model import (
    Action,
    Boundary,
    ComponentUse,
    DatasetSpec,
    Decision,
    PipelineSpec,
)
from rlab.manifests.dataset import DatasetManifest
from rlab.references import parse_reference
from rlab.references.refs import ReferenceKind
from rlab.registry.store import Registry
from rlab.typing import JsonValue

RECORD_STAGE_KINDS = (EntryKind.TRANSFORM, EntryKind.FILTER)
BATCH_STAGE_KINDS = (EntryKind.GROUP, EntryKind.DEDUP)


@lru_cache(maxsize=256)
def _method_arity(cls: type, method_name: str) -> int:
    method = getattr(cls, method_name, None)
    if method is None:
        return 0
    params = [p for p in inspect.signature(method).parameters if p != "self"]
    return len(params)


@dataclass(slots=True)
class BuildMetadata:
    component_ids: list[str] = field(default_factory=list)
    configuration: dict[str, dict[str, JsonValue]] = field(default_factory=dict)

    def track(self, component_id: str, component: ComponentUse) -> None:
        self.component_ids.append(component_id)
        self.configuration[component_id] = component_configuration(component)


@dataclass(slots=True)
class BuildResults:
    outputs: dict[str, Path] = field(default_factory=dict)
    stats: dict[str, JsonValue] = field(default_factory=dict)
    checks: dict[str, str] = field(default_factory=dict)
    licenses: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RecordStageContext:
    stage_id: str
    source_id: str
    data: DataContext
    audit: AuditRecorder


@dataclass(slots=True)
class DatasetExecution:
    registry: Registry
    data: DataContext
    output_root: Path
    audit: AuditRecorder
    metadata: BuildMetadata = field(default_factory=BuildMetadata)


def build_dataset(
    registry: Registry,
    name: str,
    ctx: DataContext,
    output_root: Path,
    *,
    overrides: dict[str, JsonValue] | None = None,
) -> DatasetManifest:
    dataset, pipeline = _resolve_dataset(registry, name, overrides or {})
    execution = DatasetExecution(
        registry=registry,
        data=ctx,
        output_root=output_root,
        audit=AuditRecorder(output_root / "audit", dataset.audit),
    )
    source_id, items = _read_source(execution, dataset.source)
    data = _execute_pipeline(execution, pipeline, items, source_id)
    results = _write_sinks(execution, dataset, data)
    _evaluate_checks(execution, dataset, data, results)
    _measure_metrics(execution, dataset, data, results)
    if not results.outputs:
        raise ValueError("dataset must produce at least one output")

    audit_paths = execution.audit.write()
    stage_prefixes = tuple(f"{kind.value}:" for kind in (*RECORD_STAGE_KINDS, *BATCH_STAGE_KINDS))
    manifest = dataset_manifest(
        name,
        dataset.version,
        results.outputs,
        inputs=(source_id,),
        stages=tuple(
            component_id
            for component_id in execution.metadata.component_ids
            if component_id.startswith(stage_prefixes)
        ),
        stats=results.stats,
        checks=results.checks,
        declaration=f"dataset:{dataset.name}@{dataset.version}",
        pipeline=f"pipeline:{pipeline.name}@{pipeline.version}",
        components=tuple(execution.metadata.component_ids),
        configuration=execution.metadata.configuration,
        audit=audit_paths,
    )
    return manifest.model_copy(update={"licenses": tuple(dict.fromkeys(results.licenses))})


def _resolve_dataset(
    registry: Registry,
    name: str,
    overrides: dict[str, JsonValue],
) -> tuple[DatasetSpec, PipelineSpec]:
    dataset = cast(DatasetSpec, registry.get(EntryKind.DATASET, name).value)
    pipeline_reference = parse_reference(dataset.pipeline)
    if pipeline_reference.kind is not ReferenceKind.PIPELINE:
        raise TypeError(f"{dataset.pipeline!r} is not a pipeline reference")
    pipeline = cast(
        PipelineSpec,
        registry.get(EntryKind.PIPELINE, pipeline_reference.value).value,
    )
    return apply_dataset_overrides(dataset, pipeline, overrides)


def _read_source(
    execution: DatasetExecution,
    source_use: ComponentUse,
) -> tuple[str, list[object]]:
    source_record, source = instantiate_component(
        execution.registry,
        source_use,
        expected=(EntryKind.SOURCE,),
    )
    source_id = canonical_component(source_record)
    execution.metadata.track(source_id, source_use)
    source_values = list(
        source.read(execution.data) if _method_arity(type(source), "read") > 0 else source.read()
    )
    execution.audit.record_source(
        source_id,
        read=len(source_values),
        emitted=len(source_values),
    )
    return source_id, list(source_values)


def _execute_pipeline(
    execution: DatasetExecution,
    pipeline: PipelineSpec,
    initial_items: list[object],
    source_id: str,
) -> tuple[object, ...]:
    items = initial_items
    for stage_use in pipeline.stages:
        stage_record, stage = instantiate_component(
            execution.registry,
            stage_use,
            expected=(*RECORD_STAGE_KINDS, *BATCH_STAGE_KINDS),
        )
        stage_id = canonical_component(stage_record)
        execution.metadata.track(stage_id, stage_use)
        received = len(items)
        if stage_record.kind in RECORD_STAGE_KINDS:
            stage_ctx = RecordStageContext(
                stage_id,
                source_id,
                execution.data,
                execution.audit,
            )
            items = _apply_record_stage(items, stage, stage_ctx)
        else:
            items = list(
                stage.apply(items, execution.data) if _method_arity(type(stage), "apply") > 1
                else stage.apply(items)
            )
        execution.audit.record_stage(stage_id, received=received, emitted=len(items))

    boundaries = [item for item in items if isinstance(item, Boundary)]
    if boundaries:
        reasons = ", ".join(sorted({b.reason for b in boundaries}))
        raise ValueError(f"pipeline left {len(boundaries)} unconsumed boundaries: {reasons}")
    return tuple(items)


def _write_sinks(
    execution: DatasetExecution,
    dataset: DatasetSpec,
    data: tuple[object, ...],
) -> BuildResults:
    results = BuildResults()
    for sink_use in dataset.sinks:
        sink_record, sink = instantiate_component(
            execution.registry,
            sink_use,
            expected=(EntryKind.SINK,),
        )
        sink_id = canonical_component(sink_record)
        execution.metadata.track(sink_id, sink_use)
        sink_result = (
            sink.write(data, execution.data) if _method_arity(type(sink), "write") > 1
            else sink.write(data)
        )
        for output_id, path in sink_result.outputs.items():
            key = str(output_id)
            if key in results.outputs:
                raise ValueError(f"duplicate dataset output: {key}")
            results.outputs[key] = _validated_output(execution.output_root, path)
        results.stats.update(sink_result.stats)
        results.checks.update(sink_result.checks)
        results.licenses.extend(sink_result.licenses)
    return results


def _evaluate_checks(
    execution: DatasetExecution,
    dataset: DatasetSpec,
    data: tuple[object, ...],
    results: BuildResults,
) -> None:
    for check_use in dataset.checks:
        check_record, check = instantiate_component(
            execution.registry,
            check_use,
            expected=(EntryKind.CHECK,),
        )
        check_id = canonical_component(check_record)
        execution.metadata.track(check_id, check_use)
        result = (
            check.evaluate(data, execution.data) if _method_arity(type(check), "evaluate") > 1
            else check.evaluate(data)
        )
        results.checks[check_id] = result.manifest_status
        for key, value in result.metrics.items():
            results.stats[f"{check_id}.{key}"] = value


def _measure_metrics(
    execution: DatasetExecution,
    dataset: DatasetSpec,
    data: tuple[object, ...],
    results: BuildResults,
) -> None:
    for metric_use in dataset.metrics:
        metric_record, metric = instantiate_component(
            execution.registry,
            metric_use,
            expected=(EntryKind.METRIC,),
        )
        metric_id = canonical_component(metric_record)
        execution.metadata.track(metric_id, metric_use)
        results.stats[metric_id] = (
            metric.measure(data, execution.data) if _method_arity(type(metric), "measure") > 1
            else metric.measure(data)
        )


def _apply_record_stage(
    items: list[object],
    stage: Any,
    stage_ctx: RecordStageContext,
) -> list[object]:
    output: list[object] = []
    for position, item in enumerate(items):
        if isinstance(item, Boundary):
            output.append(item)
            continue
        decision = (
            stage.apply(item, stage_ctx.data) if _method_arity(type(stage), "apply") > 1
            else stage.apply(item)
        )
        if not isinstance(decision, Decision):
            raise TypeError(f"{stage_ctx.stage_id} must return Decision")
        stage_ctx.audit.record_decision(
            stage=stage_ctx.stage_id,
            source=stage_ctx.source_id,
            position=position,
            decision=decision,
            input_record=item,
        )
        if decision.action in (Action.KEEP, Action.UPDATE):
            output.append(decision.record)
        elif decision.action is Action.BOUNDARY:
            output.append(Boundary(decision.reason, decision.metrics))
    return output


def _validated_output(output_root: Path, path: Path) -> Path:
    root = output_root.resolve()
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"dataset output must be inside {output_root}: {path}")
    if not resolved.exists():
        raise FileNotFoundError(f"dataset output does not exist: {path}")
    return resolved
