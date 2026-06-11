"""Python host process used by the Rust CLI for imports and user callables."""

from __future__ import annotations

import json
import math
import os
import shutil
import traceback
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias

from ._loader import load_modules
from ._protocol import (
    PROTOCOL_VERSION,
    HostRequest,
    base_event,
    emit_event,
    read_request,
)

JsonDict: TypeAlias = dict[str, Any]
MetricMap: TypeAlias = dict[str, float]


def _rfc3339_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _metric_payload(
    name: str,
    value: float,
    *,
    unit: str | None = None,
    direction: str | None = None,
) -> JsonDict:
    return {
        "schema_version": 1,
        "name": str(name),
        "value": float(value),
        "unit": unit,
        "direction": direction,
        "timestamp": _rfc3339_now(),
    }


def _metric_event(request: HostRequest, name: str, value: float) -> JsonDict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request.request_id,
        "event_type": "metric",
        "metric": _metric_payload(name, value),
    }


def _emit_completed(request: HostRequest, data: Any) -> None:
    event = base_event(request, "completed")
    event["result"] = {"schema_version": 1, "data": _jsonable(data)}
    emit_event(event)


def _emit_registry_records(request: HostRequest, records: Iterable[JsonDict]) -> None:
    for record in records:
        event = base_event(request, "registry_record")
        event["record"] = record
        emit_event(event)


def _emit_failure(request_id: str, exc: Exception) -> None:
    emit_event(
        {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request_id,
            "event_type": "failed",
            "error": {
                "schema_version": 1,
                "kind": "python_exception",
                "message": f"{type(exc).__name__}: {exc}",
                "safe_traceback": traceback.format_exc(),
                "source": "rlab._runner",
            },
        }
    )


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


class RuntimeContext:
    """Runtime context passed to Python user callables."""

    def __init__(self, request: HostRequest) -> None:
        self.run_id = request.run_id
        self.params = dict(request.params)
        self.seed = request.seed
        self.project_root = Path(request.project_root)
        self._request = request
        self._metrics: MetricMap = {}

    def log_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        direction: str | None = None,
    ) -> None:
        """Emit one metric event."""
        metric_value = float(value)
        event = base_event(self._request, "metric")
        event["metric"] = _metric_payload(
            name,
            metric_value,
            unit=unit,
            direction=direction,
        )
        emit_event(event)
        self._metrics[str(name)] = metric_value

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """Emit multiple metric events as one protocol batch."""
        events = []

        for name, value in metrics.items():
            metric_value = float(value)
            events.append(_metric_event(self._request, name, metric_value))
            self._metrics[str(name)] = metric_value

        event = base_event(self._request, "batch")
        event["events"] = events
        emit_event(event)

    def note(self, text: str) -> None:
        """Emit a log event."""
        event = base_event(self._request, "log")
        event["message"] = str(text)
        emit_event(event)

    def save_artifact(
        self, name: str, path: str | Path, *, version: str = "1", kind: str = "file"
    ) -> Path:
        """Emit an artifact event for a user-created file."""
        source = _resolve_project_path(self.project_root, path)
        if not source.exists():
            raise FileNotFoundError(f"artifact path does not exist: {source}")

        event = base_event(self._request, "artifact")
        event["artifact"] = {
            "schema_version": 1,
            "kind": kind,
            "name": str(name),
            "path": str(source),
            "version": str(version),
        }
        emit_event(event)
        return source

    def save_table(self, name: str, rows: list[dict[str, Any]]) -> Path:
        """Write a JSON table next to the project and emit it as an artifact."""
        output = self.project_root / ".rlab" / "tmp" / f"{name}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        return self.save_artifact(name, output, kind="table")

    def copy_artifact(
        self,
        name: str,
        source: str | Path,
        destination: str | Path,
        *,
        version: str = "1",
    ) -> Path:
        """Copy an artifact to a destination and emit it."""
        src = Path(source)
        dst = _resolve_project_path(self.project_root, destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return self.save_artifact(name, dst, version=version)


def main() -> int:
    request_id = "unknown"

    try:
        request = read_request()
        request_id = request.request_id

        os.environ["RLAB_RUNNER_STRICT"] = "1" if request.strict else "0"

        project = load_modules(
            request.project_root,
            request.modules,
            strict=request.strict,
        )

        _emit_registry_records(request, project.records)

        if request.command == "execute":
            _execute(request, project)
        else:
            _emit_completed(request, {"ok": True})

        return 0
    except Exception as exc:
        _emit_failure(request_id, exc)
        return 0


def _execute(request: HostRequest, project: Any) -> None:
    if request.target is None:
        raise ValueError("execute request missing target")

    ctx = RuntimeContext(request)
    result = _execute_target(request, project, ctx)

    # Emit one metric event per scalar value in the returned dict so the
    # Rust CLI can append them to metrics.jsonl (and metrics_summary.json
    # gets populated on completion). Lists and non-numeric values are
    # skipped — they will still appear under the Completed result payload.
    if isinstance(result, dict):
        _emit_dict_metrics(ctx, result, prefix="")

    _emit_completed(request, result)


def _execute_target(request: HostRequest, project: Any, ctx: RuntimeContext) -> Any:
    if request.target is None:
        raise ValueError("execute request missing target")

    if request.target.kind == "dataset":
        return _execute_dataset(request, project, ctx)
    if request.target.kind == "study":
        return _execute_study(request, project, ctx)
    if request.target.kind == "workflow":
        return _execute_workflow(request, project, ctx)

    callable_obj = project.resolve(request.target.kind, request.target.name)
    return _invoke_target(request, project, callable_obj, ctx)


def _emit_dict_metrics(ctx: RuntimeContext, value: Any, prefix: str) -> None:
    """Flatten `value` into per-leaf metric events under dotted keys."""
    flat: MetricMap = {}

    def _walk(node: Any, path: str) -> None:
        if _is_finite_number(node):
            if path:
                flat[path] = float(node)
            return

        if isinstance(node, Mapping):
            for key, child in node.items():
                child_path = f"{path}.{key}" if path else str(key)
                _walk(child, child_path)
            return

        if isinstance(node, list):
            for index, child in enumerate(node):
                child_path = f"{path}.{index}" if path else str(index)
                _walk(child, child_path)

    _walk(value, prefix)

    if flat:
        ctx.log_metrics(flat)


def _execute_workflow(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("workflow execution missing target")

    workflow_name = request.target.name
    record = project.record("workflow", workflow_name)
    steps = record.get("metadata", {}).get("steps", [])

    if not isinstance(steps, list) or not steps:
        raise ValueError(f"workflow {workflow_name!r} does not declare steps")

    outputs = [
        _execute_workflow_step(project, ctx, workflow_name, step, index)
        for index, step in enumerate(steps)
    ]

    return {"workflow": workflow_name, "steps": outputs}


def _execute_workflow_step(
    project: Any,
    ctx: RuntimeContext,
    workflow_name: str,
    step: Any,
    index: int,
) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise ValueError("workflow step metadata must be an object")

    name = str(step.get("name", f"step_{index}"))
    callable_obj = project.resolve("workflow_step", f"{workflow_name}:{name}")

    ctx.note(f"running workflow step {name}")
    value = callable_obj(ctx)

    return {"name": name, "index": index, "result": _jsonable(value)}


def _execute_study(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("study execution missing target")

    study_name = request.target.name
    experiments = _study_experiments(project.record("study", study_name))

    if not experiments:
        raise ValueError(f"study {study_name!r} does not declare experiments")

    results = [
        _execute_experiment(project, ctx, experiment_name)
        for experiment_name in experiments
    ]

    return {"study": study_name, "experiments": results}


def _study_experiments(record: JsonDict) -> list[Any]:
    metadata = dict(record.get("metadata", {}))
    spec = metadata.get("spec") if isinstance(metadata.get("spec"), dict) else metadata
    experiments = spec.get("experiments", []) if isinstance(spec, dict) else []

    if not isinstance(experiments, list):
        return []

    return experiments


def _execute_experiment(
    project: Any,
    ctx: RuntimeContext,
    experiment_name: Any,
) -> dict[str, Any]:
    if not isinstance(experiment_name, str) or not experiment_name.strip():
        raise ValueError("study experiments must be non-empty strings")

    callable_obj = project.resolve("experiment", experiment_name)

    ctx.note(f"running study experiment {experiment_name}")
    value = callable_obj(ctx)

    return {"experiment": experiment_name, "result": _jsonable(value)}


def _execute_dataset(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("dataset execution missing target")

    target_name = request.target.name
    metadata = _record_metadata(project.record("dataset", target_name))

    source_obj = _resolve_dataset_source(project, target_name, metadata)
    stages = _resolve_dataset_stages(project, metadata)

    records = list(_read_source(source_obj, ctx))
    records, audit = _apply_pipeline(project, stages, records, ctx)

    sink_results = _write_dataset_sinks(project, target_name, metadata, records, ctx)

    ctx.log_metrics(
        {
            "dataset.records": float(len(records)),
            "dataset.dropped": float(audit["dropped"]),
        }
    )

    return {
        "dataset": target_name,
        "records": len(records),
        "audit": audit,
        "sinks": sink_results,
    }


def _record_metadata(record: JsonDict) -> JsonDict:
    return dict(record.get("metadata", {}))


def _resolve_dataset_source(project: Any, target_name: str, metadata: JsonDict) -> Any:
    # Prefer pre-configured runtime callables stored at registration time.
    try:
        return project.resolve("dataset_source", target_name)
    except KeyError:
        source_ref = _component_ref(metadata.get("source"), "source")
        return _instantiate(project.resolve(*source_ref.split(":", 1)))


def _resolve_dataset_stages(project: Any, metadata: JsonDict) -> list[Any]:
    pipeline_ref = _component_ref(metadata.get("pipeline"), "pipeline")
    pipeline_name = pipeline_ref.split(":", 1)[1]
    pipeline_record = project.record("pipeline", pipeline_name)
    stages = pipeline_record.get("metadata", {}).get("stages", [])

    if not isinstance(stages, list):
        return []

    return stages


def _write_dataset_sinks(
    project: Any,
    target_name: str,
    metadata: JsonDict,
    records: list[Any],
    ctx: RuntimeContext,
) -> list[Any]:
    runtime_sinks = _write_runtime_dataset_sinks(project, target_name, records, ctx)
    if runtime_sinks:
        return runtime_sinks

    return _write_metadata_dataset_sinks(project, metadata, records, ctx)


def _write_runtime_dataset_sinks(
    project: Any,
    target_name: str,
    records: list[Any],
    ctx: RuntimeContext,
) -> list[Any]:
    sink_results = []
    sink_index = 0

    while True:
        try:
            sink = project.resolve("dataset_sink", f"{target_name}:{sink_index}")
        except KeyError:
            return sink_results

        sink_results.append(_write_sink(sink, records, ctx))
        sink_index += 1


def _write_metadata_dataset_sinks(
    project: Any,
    metadata: JsonDict,
    records: list[Any],
    ctx: RuntimeContext,
) -> list[Any]:
    sink_results = []

    for sink_value in metadata.get("sinks", []) or []:
        sink_ref = _component_ref(sink_value, "sink")
        sink = _instantiate(project.resolve(*sink_ref.split(":", 1)))
        sink_results.append(_write_sink(sink, records, ctx))

    return sink_results


def _component_ref(value: Any, default_kind: str) -> str:
    if isinstance(value, str):
        return value if ":" in value else f"{default_kind}:{value}"

    if isinstance(value, dict):
        ref = value.get("ref") or value.get("reference") or value.get("name")
        if isinstance(ref, str):
            return ref if ":" in ref else f"{default_kind}:{ref}"

    raise ValueError(f"invalid {default_kind} reference: {value!r}")


def _instantiate(value: Any) -> Any:
    if isinstance(value, type):
        return value()
    return value


def _read_source(source: Any, ctx: RuntimeContext) -> list[Any]:
    if hasattr(source, "read"):
        records = _call_with_optional_context(source.read, ctx)
    elif callable(source):
        records = _call_with_optional_context(source, ctx)
    else:
        raise ValueError("source must be callable or implement read(ctx)")

    return list(records)


def _apply_pipeline(
    project: Any, stages: list[Any], records: list[Any], ctx: RuntimeContext
) -> tuple[list[Any], dict[str, Any]]:
    current: list[Any] = records
    dropped = 0
    reasons: dict[str, int] = {}
    stage_counts: list[dict[str, Any]] = []

    for stage_ref_value in stages:
        stage_ref = _component_ref(stage_ref_value, "transform")
        stage_kind, stage_name = stage_ref.split(":", 1)
        stage = _build_stage(project, stage_kind, stage_name, stage_ref_value)

        previous = current

        if _is_batch_stage(stage, stage_kind):
            current = list(stage.apply(previous))
            stage_counts.append(_stage_count(stage_ref, previous, current))
            continue

        current, stage_dropped, stage_reasons = _apply_record_stage(
            stage,
            stage_name,
            previous,
            ctx,
        )
        dropped += stage_dropped
        _merge_reason_counts(reasons, stage_reasons)
        stage_counts.append(_stage_count(stage_ref, previous, current))

    return current, {"dropped": dropped, "reasons": reasons, "stages": stage_counts}


def _build_stage(
    project: Any,
    stage_kind: str,
    stage_name: str,
    stage_ref_value: Any,
) -> Any:
    stage_class = project.resolve(stage_kind, stage_name)

    if not isinstance(stage_ref_value, dict):
        return _instantiate(stage_class)

    config = {key: value for key, value in stage_ref_value.items() if key != "ref"}
    return stage_class(**config) if config else _instantiate(stage_class)


def _is_batch_stage(stage: Any, stage_kind: str) -> bool:
    return hasattr(stage, "apply") and stage_kind in {"dedup", "group"}


def _apply_record_stage(
    stage: Any,
    stage_name: str,
    records: list[Any],
    ctx: RuntimeContext,
) -> tuple[list[Any], int, dict[str, int]]:
    next_records: list[Any] = []
    dropped = 0
    reasons: dict[str, int] = {}

    for record in records:
        decision = _apply_stage(stage, record, ctx)
        action = getattr(decision, "action", None)

        if action == "drop":
            dropped += 1
            reason = str(getattr(decision, "reason", None) or stage_name)
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        next_records.append(_record_from_decision(decision, record, action))

    return next_records, dropped, reasons


def _record_from_decision(decision: Any, record: Any, action: Any) -> Any:
    if action == "boundary":
        from rlab.data import DataBoundary

        return DataBoundary(
            value=getattr(decision, "record", None),
            kind=str(getattr(decision, "kind", "") or ""),
        )

    if action in {"keep", "update"}:
        return getattr(decision, "record", record)

    return record


def _stage_count(stage_ref: str, records: list[Any], output: list[Any]) -> JsonDict:
    return {"stage": stage_ref, "input": len(records), "output": len(output)}


def _merge_reason_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for reason, count in source.items():
        target[reason] = target.get(reason, 0) + count


def _apply_stage(stage: Any, record: dict[str, Any], ctx: RuntimeContext) -> Any:
    if hasattr(stage, "apply"):
        return _call_with_optional_context(stage.apply, record, ctx)

    if callable(stage):
        return _call_with_optional_context(stage, record, ctx)

    raise ValueError("pipeline stage must be callable or implement apply(record, ctx)")


def _write_sink(sink: Any, records: list[dict[str, Any]], ctx: RuntimeContext) -> Any:
    if hasattr(sink, "write"):
        return _jsonable(_call_with_optional_context(sink.write, records, ctx))

    if callable(sink):
        return _jsonable(_call_with_optional_context(sink, records, ctx))

    raise ValueError("sink must be callable or implement write(records, ctx)")


def _call_with_optional_context(callable_obj: Any, *args: Any) -> Any:
    try:
        return callable_obj(*args)
    except TypeError:
        return callable_obj(*args[:-1])


def _invoke_target(
    request: HostRequest, project: Any, callable_obj: Any, ctx: RuntimeContext
) -> Any:
    if request.target is None:
        raise ValueError("execute request missing target")

    target_ref = ctx.params.get("target")
    if isinstance(target_ref, str) and target_ref:
        target = _resolve_component(project, target_ref)
        return callable_obj(target, ctx)

    return callable_obj(ctx)


def _resolve_component(project: Any, reference: Any) -> Any:
    """Resolve a `<kind>:<name>` reference.

    A two-segment reference of the form `<kind>:<loader>:<path>` is
    dispatched to the component registered at `("loader", <loader>)`
    via its `.load(path)` method. This is how a user invokes a loader
    for any vendor (HuggingFace, GGUF, S3, ...) without rlab knowing
    about the vendor — the user registers the loader themselves.
    """
    if not isinstance(reference, str) or ":" not in reference:
        raise ValueError(f"component reference must be kind:name, got {reference!r}")

    head, rest = reference.split(":", 1)

    if ":" in rest:
        return _resolve_loaded_component(project, rest)

    component = project.resolve(head, rest)
    return _materialize_component(component)


def _resolve_loaded_component(project: Any, rest: str) -> Any:
    loader_name, path = rest.split(":", 1)

    try:
        loader = project.resolve("loader", loader_name)
    except KeyError as exc:
        raise KeyError(f"no loader registered for loader:{loader_name}") from exc

    loader = _materialize_component(loader)

    load = getattr(loader, "load", None)
    if not callable(load):
        raise ValueError(f"loader:{loader_name} does not implement .load(path)")

    return load(path)


def _materialize_component(component: Any) -> Any:
    if isinstance(component, type):
        return component()

    if callable(component) and not hasattr(component, "__dict__"):
        return component()

    return component


def _resolve_project_path(project_root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else project_root / candidate


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


if __name__ == "__main__":
    raise SystemExit(main())
