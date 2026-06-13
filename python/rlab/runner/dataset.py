"""Dataset execution helpers."""

from __future__ import annotations

import csv
import json
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from rlab._project import Project
from rlab._typing import JsonObject, JsonValue

from .constants import *
from .serde import (
    accepts_args,
    call_with_optional_context,
    jsonable,
    mapping_value,
    number_value,
    pretty_json,
)

if TYPE_CHECKING:
    from .context import RuntimeContext


def execute_dataset(
    request: object, project: Project, ctx: "RuntimeContext"
) -> JsonObject:
    target = getattr(request, "target", None)
    if target is None:
        raise ValueError(ERROR_DATASET_TARGET)

    target_name = target.name
    metadata = dict(
        mapping_value(
            project.record(KIND_DATASET, target_name).get(KEY_METADATA),
            "dataset metadata",
        )
    )
    source = resolve_dataset_source(project, target_name, metadata)
    records, audit = apply_pipeline(
        project,
        resolve_dataset_stages(project, metadata),
        list(read_source(source, ctx)),
        ctx,
    )

    write_dataset_audit(ctx, audit, records)
    sinks = write_dataset_sinks(project, target_name, metadata, records, ctx)
    ctx.log_metrics(
        {
            "dataset.records": float(len(records)),
            "dataset.dropped": float(number_value(audit[KEY_DROPPED], "audit dropped")),
        }
    )

    return {
        KEY_DATASET: target_name,
        KEY_RECORDS: len(records),
        KEY_AUDIT: audit,
        KEY_SINKS: sinks,
    }


def write_dataset_audit(
    ctx: "RuntimeContext", audit: JsonObject, records: list[object]
) -> None:
    output = ctx.run_dir / DIR_ARTIFACTS / DIR_DATASET / DIR_AUDIT
    output.mkdir(parents=True, exist_ok=True)

    (output / FILE_SUMMARY_JSON).write_text(
        pretty_json(jsonable(audit)), encoding=ENCODING
    )
    write_audit_reasons(output, audit)
    write_audit_stages(output, audit)
    write_audit_sources(output, records)


def write_audit_reasons(output: Path, audit: JsonObject) -> None:
    reasons = mapping_value(audit.get(KEY_REASONS), "audit reasons")
    write_csv(
        output / FILE_DROP_REASONS, CSV_DROP_REASONS_HEADER, sorted(reasons.items())
    )


def write_audit_stages(output: Path, audit: JsonObject) -> None:
    stages = audit.get(KEY_STAGES, [])
    if not isinstance(stages, list):
        raise TypeError(ERROR_AUDIT_STAGES)

    write_csv(
        output / FILE_STAGE_SUMMARY,
        CSV_STAGE_SUMMARY_HEADER,
        (
            (stage[KEY_STAGE], stage[KEY_INPUT], stage[KEY_OUTPUT])
            for stage_value in stages
            for stage in (mapping_value(stage_value, "audit stage"),)
        ),
    )


def write_audit_sources(output: Path, records: list[object]) -> None:
    sources = Counter(
        str(getattr(record, KEY_SOURCE))
        for record in records
        if getattr(record, KEY_SOURCE, None) is not None
    )
    write_csv(
        output / FILE_SOURCE_SUMMARY, CSV_SOURCE_SUMMARY_HEADER, sorted(sources.items())
    )


def write_csv(
    path: Path, header: tuple[str, ...], rows: Iterable[tuple[object, ...]]
) -> None:
    with path.open(CSV_WRITE_MODE, encoding=ENCODING, newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


def resolve_dataset_source(
    project: Project, target_name: str, metadata: JsonObject
) -> object:
    source = resolve_optional(project, KIND_DATASET_SOURCE, target_name)
    if source is not None:
        return source

    kind, name = split_ref(component_ref(metadata.get(KEY_SOURCE), KEY_SOURCE))
    return instantiate(project.resolve(kind, name))


def resolve_dataset_stages(project: Project, metadata: JsonObject) -> list[JsonValue]:
    pipeline_ref = component_ref(metadata.get(KEY_PIPELINE), KEY_PIPELINE)
    pipeline_name = split_ref(pipeline_ref)[1]
    pipeline_metadata = mapping_value(
        project.record(KEY_PIPELINE, pipeline_name).get(KEY_METADATA),
        "pipeline metadata",
    )
    stages = pipeline_metadata.get(KEY_STAGES, [])
    return stages if isinstance(stages, list) else []


def write_dataset_sinks(
    project: Project,
    target_name: str,
    metadata: JsonObject,
    records: list[object],
    ctx: "RuntimeContext",
) -> list[JsonValue]:
    runtime_sinks = write_runtime_dataset_sinks(project, target_name, records, ctx)
    return runtime_sinks or write_metadata_dataset_sinks(
        project, metadata, records, ctx
    )


def write_runtime_dataset_sinks(
    project: Project,
    target_name: str,
    records: list[object],
    ctx: "RuntimeContext",
) -> list[JsonValue]:
    return [
        write_sink(sink, records, ctx)
        for sink in iter_runtime_dataset_sinks(project, target_name)
    ]


def iter_runtime_dataset_sinks(project: Project, target_name: str) -> Iterable[object]:
    callables = getattr(project, "_callables", {})
    if not isinstance(callables, Mapping):
        return ()

    prefix = f"{target_name}:"
    pairs = (
        (int(name.removeprefix(prefix)), callable_obj)
        for (kind, name), callable_obj in callables.items()
        if kind == KIND_DATASET_SINK and name.startswith(prefix)
    )
    return tuple(sink for _, sink in sorted(pairs, key=lambda item: item[0]))


def write_metadata_dataset_sinks(
    project: Project,
    metadata: JsonObject,
    records: list[object],
    ctx: "RuntimeContext",
) -> list[JsonValue]:
    sink_values = metadata.get(KEY_SINKS, [])
    if not isinstance(sink_values, list):
        raise TypeError(ERROR_DATASET_SINKS)

    return [
        write_sink(
            instantiate(project.resolve(*split_ref(component_ref(value, "sink")))),
            records,
            ctx,
        )
        for value in sink_values
    ]


def component_ref(value: object, default_kind: str) -> str:
    if isinstance(value, str):
        return namespaced_ref(value, default_kind)

    if isinstance(value, dict):
        ref = value.get(KEY_REF) or value.get(KEY_REFERENCE) or value.get(KEY_NAME)
        if isinstance(ref, str):
            return namespaced_ref(ref, default_kind)

    raise ValueError(ERROR_REF.format(kind=default_kind, value=value))


def namespaced_ref(value: str, default_kind: str) -> str:
    return value if REF_SEPARATOR in value else f"{default_kind}:{value}"


def split_ref(value: str) -> tuple[str, str]:
    head, tail = value.split(REF_SEPARATOR, 1)
    return head, tail


def instantiate(value: object) -> object:
    return cast(Callable[[], object], value)() if isinstance(value, type) else value


def read_source(source: object, ctx: "RuntimeContext") -> list[object]:
    read = getattr(source, "read", None)
    if callable(read):
        return list(cast(Iterable[object], call_with_optional_context(read, ctx)))
    if callable(source):
        return list(cast(Iterable[object], call_with_optional_context(source, ctx)))
    raise ValueError(ERROR_SOURCE_CALLABLE)


def apply_pipeline(
    project: Project,
    stages: list[JsonValue],
    records: list[object],
    ctx: "RuntimeContext",
) -> tuple[list[object], JsonObject]:
    current = records
    dropped = 0
    reasons: dict[str, int] = {}
    stage_counts: list[JsonObject] = []

    for value in stages:
        stage_ref = component_ref(value, KIND_TRANSFORM)
        stage_kind, stage_name = split_ref(stage_ref)
        stage = build_stage(project, stage_kind, stage_name, value)
        previous = current

        if is_batch_stage(stage, stage_kind):
            current = apply_batch_stage(stage, previous)
        else:
            applier = _resolve_record_applier(stage, stage_name, ctx)
            current, stage_dropped, stage_reasons = apply_record_stage(
                applier, stage_name, previous, ctx
            )
            dropped += stage_dropped
            merge_reason_counts(reasons, stage_reasons)

        stage_counts.append(
            {KEY_STAGE: stage_ref, KEY_INPUT: len(previous), KEY_OUTPUT: len(current)}
        )

    return current, {
        KEY_DROPPED: dropped,
        KEY_REASONS: cast(JsonObject, reasons),
        KEY_STAGES: cast(list[JsonValue], stage_counts),
    }


def build_stage(
    project: Project, stage_kind: str, stage_name: str, stage_ref_value: object
) -> object:
    stage_class = project.resolve(stage_kind, stage_name)
    config = (
        {key: value for key, value in stage_ref_value.items() if key != KEY_REF}
        if isinstance(stage_ref_value, dict)
        else {}
    )
    return (
        cast(Callable[..., object], stage_class)(**config)
        if config
        else instantiate(stage_class)
    )


def is_batch_stage(stage: object, stage_kind: str) -> bool:
    return hasattr(stage, "apply") and stage_kind in {KIND_DEDUP, KIND_GROUP}


def apply_batch_stage(stage: object, records: list[object]) -> list[object]:
    apply = getattr(stage, "apply", None)
    if not callable(apply):
        raise ValueError(ERROR_BATCH_APPLY)

    applied = cast(Callable[[list[object]], object], apply)(records)
    if not isinstance(applied, Iterable):
        raise TypeError(ERROR_BATCH_OUTPUT)

    return list(applied)


def _resolve_record_applier(
    stage: object, stage_name: str, ctx: "RuntimeContext"
) -> Callable[[object], object]:
    """Probe arity once per stage so the record loop pays no inspect overhead."""
    fn = getattr(stage, "apply", None)
    if callable(fn):
        fn = cast(Callable[..., object], fn)
    elif callable(stage):
        fn = cast(Callable[..., object], stage)
    else:
        raise ValueError(ERROR_STAGE_CALLABLE)
    if accepts_args(fn, (None, ctx)):
        return lambda record: fn(record, ctx)
    return lambda record: fn(record)


def apply_record_stage(
    applier: Callable[[object], object],
    stage_name: str,
    records: list[object],
    ctx: "RuntimeContext",
) -> tuple[list[object], int, dict[str, int]]:
    next_records: list[object] = []
    dropped = 0
    reasons: dict[str, int] = {}

    for record in records:
        decision = applier(record)
        action = getattr(decision, "action", None)

        if action == ACTION_DROP:
            dropped += 1
            reason = str(getattr(decision, KEY_REASON, None) or stage_name)
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        next_records.append(record_from_decision(decision, record, action))

    return next_records, dropped, reasons


def record_from_decision(decision: object, record: object, action: object) -> object:
    if action == ACTION_BOUNDARY:
        from rlab.data import DataBoundary

        return DataBoundary(
            value=getattr(decision, KEY_RECORD, None),
            kind=str(getattr(decision, KEY_KIND, "") or ""),
        )

    if action in {ACTION_KEEP, ACTION_UPDATE}:
        return getattr(decision, KEY_RECORD, record)

    return record


def merge_reason_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for reason, count in source.items():
        target[reason] = target.get(reason, 0) + count


def call_stage_like(obj: object, method: str, err: str, *args: object) -> object:
    fn = getattr(obj, method, None)
    if callable(fn):
        return call_with_optional_context(fn, *args)
    if callable(obj):
        return call_with_optional_context(obj, *args)
    raise ValueError(err)


def write_sink(sink: object, records: list[object], ctx: "RuntimeContext") -> JsonValue:
    return jsonable(call_stage_like(sink, "write", ERROR_SINK_CALLABLE, records, ctx))


def resolve_optional(project: Project, kind: str, name: str) -> object | None:
    callables = getattr(project, "_callables", {})
    if not isinstance(callables, Mapping):
        return None
    return callables.get((kind, name))
