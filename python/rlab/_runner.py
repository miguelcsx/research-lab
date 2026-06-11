"""Python host process used by the Rust CLI for imports and user callables."""

from __future__ import annotations

import json
import os
import shutil
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ._loader import load_modules
from ._protocol import (
    PROTOCOL_VERSION,
    HostRequest,
    base_event,
    emit_event,
    read_request,
)


def _rfc3339_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class RuntimeContext:
    """Runtime context passed to Python user callables."""

    def __init__(self, request: HostRequest) -> None:
        self.run_id = request.run_id
        self.params = dict(request.params)
        self.seed = request.seed
        self.project_root = Path(request.project_root)
        self._request = request
        self._metrics: dict[str, float] = {}

    def log_metric(
        self,
        name: str,
        value: float,
        *,
        unit: str | None = None,
        direction: str | None = None,
    ) -> None:
        """Emit one metric event."""
        metric = {
            "schema_version": 1,
            "name": str(name),
            "value": float(value),
            "unit": unit,
            "direction": direction,
            "timestamp": _rfc3339_now(),
        }
        event = base_event(self._request, "metric")
        event["metric"] = metric
        emit_event(event)
        self._metrics[str(name)] = float(value)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        """Emit multiple metric events as one protocol batch."""
        events = []
        for name, value in metrics.items():
            metric_value = float(value)
            events.append(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "request_id": self._request.request_id,
                    "event_type": "metric",
                    "metric": {
                        "schema_version": 1,
                        "name": str(name),
                        "value": metric_value,
                        "unit": None,
                        "direction": None,
                        "timestamp": _rfc3339_now(),
                    },
                }
            )
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
        source = Path(path)
        if not source.is_absolute():
            source = self.project_root / source
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
        dst = Path(destination)
        if not dst.is_absolute():
            dst = self.project_root / dst
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
            request.project_root, request.modules, strict=request.strict
        )
        for record in project.records:
            event = base_event(request, "registry_record")
            event["record"] = record
            emit_event(event)
        if request.command == "execute":
            _execute(request, project)
        else:
            event = base_event(request, "completed")
            event["result"] = {"schema_version": 1, "data": {"ok": True}}
            emit_event(event)
        return 0
    except Exception as exc:
        fallback = {
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
        emit_event(fallback)
        return 0


def _execute(request: HostRequest, project: Any) -> None:
    if request.target is None:
        raise ValueError("execute request missing target")
    ctx = RuntimeContext(request)
    if request.target.kind == "dataset":
        result = _execute_dataset(request, project, ctx)
    elif request.target.kind == "study":
        result = _execute_study(request, project, ctx)
    elif request.target.kind == "workflow":
        result = _execute_workflow(request, project, ctx)
    else:
        callable_obj = project.resolve(request.target.kind, request.target.name)
        result = _invoke_target(request, project, callable_obj, ctx)
    event = base_event(request, "completed")
    event["result"] = {"schema_version": 1, "data": _jsonable(result)}
    emit_event(event)


def _execute_workflow(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("workflow execution missing target")
    record = project.record("workflow", request.target.name)
    steps = record.get("metadata", {}).get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"workflow {request.target.name!r} does not declare steps")
    outputs: list[dict[str, Any]] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise ValueError("workflow step metadata must be an object")
        name = str(step.get("name", f"step_{index}"))
        callable_obj = project.resolve("workflow_step", f"{request.target.name}:{name}")
        ctx.note(f"running workflow step {name}")
        value = callable_obj(ctx)
        outputs.append({"name": name, "index": index, "result": _jsonable(value)})
    return {"workflow": request.target.name, "steps": outputs}


def _execute_study(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("study execution missing target")
    record = project.record("study", request.target.name)
    metadata = dict(record.get("metadata", {}))
    spec = metadata.get("spec") if isinstance(metadata.get("spec"), dict) else metadata
    experiments = spec.get("experiments", []) if isinstance(spec, dict) else []
    if not isinstance(experiments, list) or not experiments:
        raise ValueError(f"study {request.target.name!r} does not declare experiments")
    results: list[dict[str, Any]] = []
    for experiment_name in experiments:
        if not isinstance(experiment_name, str) or not experiment_name.strip():
            raise ValueError("study experiments must be non-empty strings")
        callable_obj = project.resolve("experiment", experiment_name)
        ctx.note(f"running study experiment {experiment_name}")
        value = callable_obj(ctx)
        results.append({"experiment": experiment_name, "result": _jsonable(value)})
    return {"study": request.target.name, "experiments": results}


def _execute_dataset(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("dataset execution missing target")
    target_name = request.target.name
    record = project.record("dataset", target_name)
    metadata = dict(record.get("metadata", {}))

    # Prefer pre-configured runtime callables stored at registration time.
    try:
        source_obj = project.resolve("dataset_source", target_name)
    except KeyError:
        source_ref = _component_ref(metadata.get("source"), "source")
        source_obj = _instantiate(project.resolve(*source_ref.split(":", 1)))

    pipeline_ref = _component_ref(metadata.get("pipeline"), "pipeline")
    pipeline_name = pipeline_ref.split(":", 1)[1]
    pipeline_record = project.record("pipeline", pipeline_name)
    stages = pipeline_record.get("metadata", {}).get("stages", [])

    records = list(_read_source(source_obj, ctx))
    records, audit = _apply_pipeline(project, stages, records, ctx)

    sink_results = []
    sink_index = 0
    while True:
        try:
            sink = project.resolve("dataset_sink", f"{target_name}:{sink_index}")
            sink_results.append(_write_sink(sink, records, ctx))
            sink_index += 1
        except KeyError:
            break
    if not sink_results:
        # Fall back to metadata refs.
        for sink_value in metadata.get("sinks", []) or []:
            sink_ref = _component_ref(sink_value, "sink")
            sink = _instantiate(project.resolve(*sink_ref.split(":", 1)))
            sink_results.append(_write_sink(sink, records, ctx))

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
        try:
            records = source.read(ctx)
        except TypeError:
            records = source.read()
    elif callable(source):
        try:
            records = source(ctx)
        except TypeError:
            records = source()
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
        stage_class = project.resolve(stage_kind, stage_name)

        # Reconstruct configured instance if the stage dict carries field values.
        if isinstance(stage_ref_value, dict):
            config = {k: v for k, v in stage_ref_value.items() if k != "ref"}
            stage = stage_class(**config) if config else _instantiate(stage_class)
        else:
            stage = _instantiate(stage_class)

        # Batch stages (dedup, group) receive the whole sequence.
        if hasattr(stage, "apply") and stage_kind in {"dedup", "group"}:
            output = list(stage.apply(current))
            stage_counts.append(
                {"stage": stage_ref, "input": len(current), "output": len(output)}
            )
            current = output
            continue

        next_records: list[Any] = []
        for record in current:
            decision = _apply_stage(stage, record, ctx)
            action = getattr(decision, "action", None)
            if action == "drop":
                dropped += 1
                reason = str(getattr(decision, "reason", None) or stage_name)
                reasons[reason] = reasons.get(reason, 0) + 1
            elif action == "boundary":
                from rlab.data import DataBoundary

                next_records.append(
                    DataBoundary(
                        value=getattr(decision, "record", None),
                        kind=str(getattr(decision, "kind", "") or ""),
                    )
                )
            elif action in {"keep", "update"}:
                next_records.append(getattr(decision, "record", record))
            else:
                next_records.append(record)
        stage_counts.append(
            {"stage": stage_ref, "input": len(current), "output": len(next_records)}
        )
        current = next_records
    return current, {"dropped": dropped, "reasons": reasons, "stages": stage_counts}


def _apply_stage(stage: Any, record: dict[str, Any], ctx: RuntimeContext) -> Any:
    if hasattr(stage, "apply"):
        try:
            return stage.apply(record, ctx)
        except TypeError:
            return stage.apply(record)
    if callable(stage):
        try:
            return stage(record, ctx)
        except TypeError:
            return stage(record)
    raise ValueError("pipeline stage must be callable or implement apply(record, ctx)")


def _write_sink(sink: Any, records: list[dict[str, Any]], ctx: RuntimeContext) -> Any:
    if hasattr(sink, "write"):
        try:
            return _jsonable(sink.write(records, ctx))
        except TypeError:
            return _jsonable(sink.write(records))
    if callable(sink):
        try:
            return _jsonable(sink(records, ctx))
        except TypeError:
            return _jsonable(sink(records))
    raise ValueError("sink must be callable or implement write(records, ctx)")


def _invoke_target(
    request: HostRequest, project: Any, callable_obj: Any, ctx: RuntimeContext
) -> Any:
    if request.target is None:
        raise ValueError("execute request missing target")
    if request.target.kind == "benchmark":
        target_ref = ctx.params.get("target_ref")
        target = _resolve_component(project, target_ref)
        return callable_obj(target, ctx)
    if request.target.kind == "evaluation":
        model_ref = ctx.params.get("model")
        model = _resolve_component(project, model_ref)
        return callable_obj(model, ctx)
    return callable_obj(ctx)


def _resolve_component(project: Any, reference: Any) -> Any:
    if not isinstance(reference, str) or ":" not in reference:
        raise ValueError("component reference must be kind:name")
    kind, name = reference.split(":", 1)
    component = project.resolve(kind, name)
    if isinstance(component, type):
        return component()
    if callable(component) and not hasattr(component, "__dict__"):
        return component()
    return component


def _jsonable(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


if __name__ == "__main__":
    raise SystemExit(main())
