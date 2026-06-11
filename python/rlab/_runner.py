"""Python host process used by the Rust CLI for imports and user callables."""

from __future__ import annotations

import hashlib
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
from ._rlab import run_external_command
from .external import (
    AdapterContext,
    ExternalCommand,
    ExternalCommandError,
    ExternalResult,
    ExternalWorkspace,
)

JsonDict: TypeAlias = dict[str, Any]
MetricMap: TypeAlias = dict[str, float]


def _rfc3339_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _metric_payload(
    name: str, value: float, *, unit: str | None = None, direction: str | None = None
) -> JsonDict:
    return {
        "schema_version": 1,
        "name": str(name),
        "value": float(value),
        "unit": unit,
        "direction": direction,
        "timestamp": _rfc3339_now(),
    }


def _event(request: HostRequest, event_type: str, **fields: Any) -> JsonDict:
    event = base_event(request, event_type)
    event.update(fields)
    return event


def _metric_event(request: HostRequest, name: str, value: float) -> JsonDict:
    return _event(request, "metric", metric=_metric_payload(name, value))


def _emit_completed(request: HostRequest, data: Any) -> None:
    emit_event(
        _event(
            request, "completed", result={"schema_version": 1, "data": _jsonable(data)}
        )
    )


def _emit_registry_records(request: HostRequest, records: Iterable[JsonDict]) -> None:
    for record in records:
        emit_event(_event(request, "registry_record", record=record))


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
        if request.run_dir is None:
            raise ValueError("runtime execution requires a resolved run_dir")
        if request.cache_dir is None:
            raise ValueError("runtime execution requires a resolved cache_dir")
        self.run_id = request.run_id
        self.run_dir = Path(request.run_dir)
        self.cache_dir = Path(request.cache_dir)
        self.output_dir = self.run_dir / "outputs"
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
        metric_value = float(value)
        emit_event(
            _event(
                self._request,
                "metric",
                metric=_metric_payload(
                    name, metric_value, unit=unit, direction=direction
                ),
            )
        )
        self._metrics[str(name)] = metric_value

    def log_metrics(self, metrics: dict[str, float]) -> None:
        flat = {str(name): float(value) for name, value in metrics.items()}
        emit_event(
            _event(
                self._request,
                "batch",
                events=[
                    _metric_event(self._request, name, value)
                    for name, value in flat.items()
                ],
            )
        )
        self._metrics.update(flat)

    def note(self, text: str) -> None:
        emit_event(_event(self._request, "log", message=str(text)))

    def save_artifact(
        self, name: str, path: str | Path, *, version: str = "1", kind: str = "file"
    ) -> Path:
        source = _resolve_project_path(self.project_root, path)
        if not source.exists():
            raise FileNotFoundError(f"artifact path does not exist: {source}")
        emit_event(
            _event(
                self._request,
                "artifact",
                artifact={
                    "schema_version": 1,
                    "kind": kind,
                    "name": str(name),
                    "path": str(source),
                    "version": str(version),
                },
            )
        )
        return source

    def save_table(self, name: str, rows: list[dict[str, Any]]) -> Path:
        output = self.run_dir / "generated" / "tables" / f"{name}.json"
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
        dst = _resolve_project_path(self.project_root, destination)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(source), dst)
        return self.save_artifact(name, dst, version=version)

    def run_external(self, name: str, command: ExternalCommand) -> ExternalResult:
        command.validate()
        output_dir = self.run_dir / "external" / _safe_external_name(name)
        output_dir.mkdir(parents=True, exist_ok=True)
        stdout_path, stderr_path = output_dir / "stdout.log", output_dir / "stderr.log"
        payload = json.loads(
            run_external_command(
                list(command.args),
                command.cwd,
                dict(command.env),
                command.timeout_seconds,
                stdout_path,
                stderr_path,
            )
        )
        result = ExternalResult(
            exit_code=payload.get("exit_code"),
            stdout=stdout_path.read_text(encoding="utf-8", errors="replace"),
            stderr=stderr_path.read_text(encoding="utf-8", errors="replace"),
            timed_out=bool(payload.get("timed_out", False)),
        )
        self.save_artifact(f"{name}.stdout", stdout_path, kind="log")
        self.save_artifact(f"{name}.stderr", stderr_path, kind="log")
        if result.timed_out or result.exit_code != 0:
            raise ExternalCommandError(name, result)
        if command.output_root is not None:
            self._register_external_artifacts(
                name, command.output_root, command.artifacts
            )
        return result

    def external_workspace(
        self, name: str, spec: ExternalWorkspace, params: Mapping[str, Any]
    ) -> AdapterContext:
        spec.validate()
        external_root = self.run_dir / "external" / _safe_external_name(name)
        outputs = external_root / "outputs"
        workspace = self._materialize_external_workspace(name, spec, params, outputs)
        return AdapterContext(
            project_root=self.project_root,
            workspace=workspace,
            outputs=outputs,
            params=dict(params),
        )

    def _materialize_external_workspace(
        self,
        name: str,
        spec: ExternalWorkspace,
        params: Mapping[str, Any],
        outputs: Path,
    ) -> Path:
        _external_root, workspace = outputs.parent, outputs.parent / "workspace"
        outputs.mkdir(parents=True, exist_ok=True)
        if workspace.exists():
            return workspace

        source = _resolve_project_path(
            self.project_root, str(params.get(spec.source_param, spec.default_source))
        )
        if not source.is_dir():
            raise FileNotFoundError(
                f"external workspace source does not exist: {source}"
            )

        cache_root = self.cache_dir / _safe_external_name(name)
        excluded = tuple(path.path for path in (*spec.cached, *spec.outputs))
        cached_workspace = (
            cache_root
            / "workspaces"
            / _workspace_fingerprint(source, spec.ignored, excluded)
        )
        if not cached_workspace.exists():
            _copy_workspace(source, cached_workspace, spec.ignored, excluded)
        if not workspace.exists():
            shutil.copytree(cached_workspace, workspace, symlinks=True)

        for path in spec.cached:
            target = cache_root / "resources" / _safe_external_name(path.name)
            source_path = source / _safe_relative_path(path.path)
            if not target.exists():
                _copy_or_mkdir(source_path, target)
            _replace_with_symlink(workspace / _safe_relative_path(path.path), target)

        for path in spec.outputs:
            target = outputs / _safe_relative_path(path.name)
            target.mkdir(parents=True, exist_ok=True)
            _replace_with_symlink(workspace / _safe_relative_path(path.path), target)

        return workspace

    def _register_external_artifacts(
        self, command_name: str, output_root: Path, patterns: tuple[str, ...]
    ) -> None:
        for path in sorted(
            {
                path
                for pattern in patterns
                for path in output_root.glob(pattern)
                if path.is_file()
            }
        ):
            stem = (
                path.relative_to(output_root)
                .with_suffix("")
                .as_posix()
                .replace("/", ".")
            )
            self.save_artifact(_bounded_artifact_name(command_name, stem), path)

    def register_outputs(self) -> None:
        if self.output_dir.exists():
            for path in sorted(
                item for item in self.output_dir.rglob("*") if item.is_file()
            ):
                stem = (
                    path.relative_to(self.output_dir)
                    .with_suffix("")
                    .as_posix()
                    .replace("/", ".")
                )
                self.save_artifact(_bounded_artifact_name("output", stem), path)


def main() -> int:
    request_id = "unknown"
    try:
        request = read_request()
        request_id = request.request_id
        os.environ["RLAB_RUNNER_STRICT"] = "1" if request.strict else "0"
        project = load_modules(
            request.project_root, request.modules, strict=request.strict
        )
        _emit_registry_records(request, project.records)
        _execute(request, project) if request.command == "execute" else _emit_completed(
            request, {"ok": True}
        )
    except Exception as exc:
        _emit_failure(request_id, exc)
    return 0


def _execute(request: HostRequest, project: Any) -> None:
    if request.target is None:
        raise ValueError("execute request missing target")
    ctx = RuntimeContext(request)
    result = _execute_target(request, project, ctx)
    ctx.register_outputs()
    if isinstance(result, dict):
        _emit_dict_metrics(ctx, result, "")
    _emit_completed(request, result)


def _execute_target(request: HostRequest, project: Any, ctx: RuntimeContext) -> Any:
    if request.target is None:
        raise ValueError("execute request missing target")
    handlers = {
        "dataset": _execute_dataset,
        "study": _execute_study,
        "workflow": _execute_workflow,
    }
    handler = handlers.get(request.target.kind)
    return (
        handler(request, project, ctx)
        if handler
        else _invoke_target(
            request,
            project,
            project.resolve(request.target.kind, request.target.name),
            ctx,
        )
    )


def _emit_dict_metrics(ctx: RuntimeContext, value: Any, prefix: str) -> None:
    flat: MetricMap = {}

    def walk(node: Any, path: str) -> None:
        if _is_finite_number(node):
            if path:
                flat[path] = float(node)
        elif isinstance(node, Mapping):
            for key, child in node.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}.{index}" if path else str(index))

    walk(value, prefix)
    if flat:
        ctx.log_metrics(flat)


def _safe_external_name(name: str) -> str:
    value = str(name).strip()
    if not value or any(part in value for part in ("/", "\\", "..")):
        raise ValueError(f"invalid external command name: {name!r}")
    return value


def _bounded_artifact_name(command_name: str, stem: str) -> str:
    value = f"{command_name}.{stem}"
    return (
        value
        if len(value) <= 180
        else f"{value[:163]}.{hashlib.sha256(value.encode()).hexdigest()[:16]}"
    )


def _execute_workflow(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("workflow execution missing target")
    workflow_name = request.target.name
    steps = (
        project.record("workflow", workflow_name).get("metadata", {}).get("steps", [])
    )
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"workflow {workflow_name!r} does not declare steps")
    return {
        "workflow": workflow_name,
        "steps": [
            _execute_workflow_step(project, ctx, workflow_name, step, index)
            for index, step in enumerate(steps)
        ],
    }


def _execute_workflow_step(
    project: Any, ctx: RuntimeContext, workflow_name: str, step: Any, index: int
) -> dict[str, Any]:
    if not isinstance(step, dict):
        raise ValueError("workflow step metadata must be an object")
    name = str(step.get("name", f"step_{index}"))
    ctx.note(f"running workflow step {name}")
    return {
        "name": name,
        "index": index,
        "result": _jsonable(
            project.resolve("workflow_step", f"{workflow_name}:{name}")(ctx)
        ),
    }


def _execute_study(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("study execution missing target")
    study_name = request.target.name
    experiments = _study_experiments(project.record("study", study_name))
    if not experiments:
        raise ValueError(f"study {study_name!r} does not declare experiments")
    return {
        "study": study_name,
        "experiments": [
            _execute_experiment(project, ctx, name) for name in experiments
        ],
    }


def _study_experiments(record: JsonDict) -> list[Any]:
    metadata = record.get("metadata", {})
    spec = (
        metadata.get("spec")
        if isinstance(metadata, dict) and isinstance(metadata.get("spec"), dict)
        else metadata
    )
    experiments = spec.get("experiments", []) if isinstance(spec, dict) else []
    return experiments if isinstance(experiments, list) else []


def _execute_experiment(
    project: Any, ctx: RuntimeContext, experiment_name: Any
) -> dict[str, Any]:
    if not isinstance(experiment_name, str) or not experiment_name.strip():
        raise ValueError("study experiments must be non-empty strings")
    ctx.note(f"running study experiment {experiment_name}")
    return {
        "experiment": experiment_name,
        "result": _jsonable(project.resolve("experiment", experiment_name)(ctx)),
    }


def _execute_dataset(
    request: HostRequest, project: Any, ctx: RuntimeContext
) -> dict[str, Any]:
    if request.target is None:
        raise ValueError("dataset execution missing target")
    target_name = request.target.name
    metadata = dict(project.record("dataset", target_name).get("metadata", {}))
    source = _resolve_dataset_source(project, target_name, metadata)
    records, audit = _apply_pipeline(
        project,
        _resolve_dataset_stages(project, metadata),
        list(_read_source(source, ctx)),
        ctx,
    )
    sinks = _write_dataset_sinks(project, target_name, metadata, records, ctx)
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
        "sinks": sinks,
    }


def _resolve_dataset_source(project: Any, target_name: str, metadata: JsonDict) -> Any:
    try:
        return project.resolve("dataset_source", target_name)
    except KeyError:
        return _instantiate(
            project.resolve(
                *_component_ref(metadata.get("source"), "source").split(":", 1)
            )
        )


def _resolve_dataset_stages(project: Any, metadata: JsonDict) -> list[Any]:
    pipeline_name = _component_ref(metadata.get("pipeline"), "pipeline").split(":", 1)[
        1
    ]
    stages = (
        project.record("pipeline", pipeline_name).get("metadata", {}).get("stages", [])
    )
    return stages if isinstance(stages, list) else []


def _write_dataset_sinks(
    project: Any,
    target_name: str,
    metadata: JsonDict,
    records: list[Any],
    ctx: RuntimeContext,
) -> list[Any]:
    return _write_runtime_dataset_sinks(
        project, target_name, records, ctx
    ) or _write_metadata_dataset_sinks(project, metadata, records, ctx)


def _write_runtime_dataset_sinks(
    project: Any, target_name: str, records: list[Any], ctx: RuntimeContext
) -> list[Any]:
    sinks, index = [], 0
    while True:
        try:
            sinks.append(
                _write_sink(
                    project.resolve("dataset_sink", f"{target_name}:{index}"),
                    records,
                    ctx,
                )
            )
            index += 1
        except KeyError:
            return sinks


def _write_metadata_dataset_sinks(
    project: Any, metadata: JsonDict, records: list[Any], ctx: RuntimeContext
) -> list[Any]:
    return [
        _write_sink(
            _instantiate(project.resolve(*_component_ref(value, "sink").split(":", 1))),
            records,
            ctx,
        )
        for value in metadata.get("sinks", []) or []
    ]


def _component_ref(value: Any, default_kind: str) -> str:
    if isinstance(value, str):
        return value if ":" in value else f"{default_kind}:{value}"
    if isinstance(value, dict):
        ref = value.get("ref") or value.get("reference") or value.get("name")
        if isinstance(ref, str):
            return ref if ":" in ref else f"{default_kind}:{ref}"
    raise ValueError(f"invalid {default_kind} reference: {value!r}")


def _instantiate(value: Any) -> Any:
    return value() if isinstance(value, type) else value


def _read_source(source: Any, ctx: RuntimeContext) -> list[Any]:
    read = getattr(source, "read", None)
    if callable(read):
        return list(_call_with_optional_context(read, ctx))
    if callable(source):
        return list(_call_with_optional_context(source, ctx))
    raise ValueError("source must be callable or implement read(ctx)")


def _apply_pipeline(
    project: Any, stages: list[Any], records: list[Any], ctx: RuntimeContext
) -> tuple[list[Any], dict[str, Any]]:
    current, dropped, reasons, stage_counts = records, 0, {}, []
    for value in stages:
        stage_ref = _component_ref(value, "transform")
        stage_kind, stage_name = stage_ref.split(":", 1)
        stage = _build_stage(project, stage_kind, stage_name, value)
        previous = current
        if _is_batch_stage(stage, stage_kind):
            current = list(stage.apply(previous))
        else:
            current, stage_dropped, stage_reasons = _apply_record_stage(
                stage, stage_name, previous, ctx
            )
            dropped += stage_dropped
            _merge_reason_counts(reasons, stage_reasons)
        stage_counts.append(
            {"stage": stage_ref, "input": len(previous), "output": len(current)}
        )
    return current, {"dropped": dropped, "reasons": reasons, "stages": stage_counts}


def _build_stage(
    project: Any, stage_kind: str, stage_name: str, stage_ref_value: Any
) -> Any:
    stage_class = project.resolve(stage_kind, stage_name)
    config = (
        {key: value for key, value in stage_ref_value.items() if key != "ref"}
        if isinstance(stage_ref_value, dict)
        else {}
    )
    return stage_class(**config) if config else _instantiate(stage_class)


def _is_batch_stage(stage: Any, stage_kind: str) -> bool:
    return hasattr(stage, "apply") and stage_kind in {"dedup", "group"}


def _apply_record_stage(
    stage: Any, stage_name: str, records: list[Any], ctx: RuntimeContext
) -> tuple[list[Any], int, dict[str, int]]:
    next_records, dropped, reasons = [], 0, {}
    for record in records:
        decision = _apply_stage(stage, record, ctx)
        action = getattr(decision, "action", None)
        if action == "drop":
            dropped += 1
            reason = str(getattr(decision, "reason", None) or stage_name)
            reasons[reason] = reasons.get(reason, 0) + 1
        else:
            next_records.append(_record_from_decision(decision, record, action))
    return next_records, dropped, reasons


def _record_from_decision(decision: Any, record: Any, action: Any) -> Any:
    if action == "boundary":
        from rlab.data import DataBoundary

        return DataBoundary(
            value=getattr(decision, "record", None),
            kind=str(getattr(decision, "kind", "") or ""),
        )
    return (
        getattr(decision, "record", record) if action in {"keep", "update"} else record
    )


def _merge_reason_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for reason, count in source.items():
        target[reason] = target.get(reason, 0) + count


def _call_stage_like(obj: Any, method: str, err: str, *args: Any) -> Any:
    fn = getattr(obj, method, None)
    if callable(fn):
        return _call_with_optional_context(fn, *args)
    if callable(obj):
        return _call_with_optional_context(obj, *args)
    raise ValueError(err)


def _apply_stage(stage: Any, record: dict[str, Any], ctx: RuntimeContext) -> Any:
    return _call_stage_like(
        stage,
        "apply",
        "pipeline stage must be callable or implement apply(record, ctx)",
        record,
        ctx,
    )


def _write_sink(sink: Any, records: list[dict[str, Any]], ctx: RuntimeContext) -> Any:
    return _jsonable(
        _call_stage_like(
            sink,
            "write",
            "sink must be callable or implement write(records, ctx)",
            records,
            ctx,
        )
    )


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
    return (
        callable_obj(_resolve_component(project, target_ref), ctx)
        if isinstance(target_ref, str) and target_ref
        else callable_obj(ctx)
    )


def _resolve_component(project: Any, reference: Any) -> Any:
    if not isinstance(reference, str) or ":" not in reference:
        raise ValueError(f"component reference must be kind:name, got {reference!r}")
    head, rest = reference.split(":", 1)
    return (
        _resolve_loaded_component(project, rest)
        if ":" in rest
        else _materialize_component(project.resolve(head, rest))
    )


def _resolve_loaded_component(project: Any, rest: str) -> Any:
    loader_name, path = rest.split(":", 1)
    try:
        loader = project.resolve("loader", loader_name)
    except KeyError as exc:
        raise KeyError(f"no loader registered for loader:{loader_name}") from exc
    load = getattr(_materialize_component(loader), "load", None)
    if not callable(load):
        raise ValueError(f"loader:{loader_name} does not implement .load(path)")
    return load(path)


def _materialize_component(component: Any) -> Any:
    return (
        component()
        if isinstance(component, type)
        or (callable(component) and not hasattr(component, "__dict__"))
        else component
    )


def _workspace_fingerprint(
    source: Path, ignored: tuple[str, ...], excluded: tuple[str, ...]
) -> str:
    digest = hashlib.sha256()
    ignored_names, excluded_paths = (
        set(ignored),
        {_safe_relative_path(path) for path in excluded},
    )
    for root, directories, filenames in os.walk(source):
        root_path = Path(root)
        relative_root = root_path.relative_to(source)
        directories[:] = sorted(
            name
            for name in directories
            if name not in ignored_names and relative_root / name not in excluded_paths
        )
        for filename in sorted(name for name in filenames if name not in ignored_names):
            path = root_path / filename
            relative = path.relative_to(source)
            if relative not in excluded_paths:
                stat = path.stat()
                digest.update(relative.as_posix().encode())
                digest.update(str(stat.st_size).encode())
                digest.update(str(stat.st_mtime_ns).encode())
    return digest.hexdigest()


def _copy_workspace(
    source: Path, destination: Path, ignored: tuple[str, ...], excluded: tuple[str, ...]
) -> None:
    ignored_names, excluded_paths = (
        set(ignored),
        {_safe_relative_path(path) for path in excluded},
    )

    def ignore(directory: str, names: list[str]) -> set[str]:
        relative_root = Path(directory).relative_to(source)
        return {
            name
            for name in names
            if name in ignored_names or relative_root / name in excluded_paths
        }

    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    temporary.parent.mkdir(parents=True, exist_ok=True)
    if temporary.exists():
        shutil.rmtree(temporary)
    shutil.copytree(source, temporary, symlinks=True, ignore=ignore)
    try:
        temporary.rename(destination)
    except OSError:
        if not destination.exists():
            raise
        shutil.rmtree(temporary)


def _copy_or_mkdir(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, symlinks=True)
    elif source.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    else:
        target.mkdir(parents=True, exist_ok=True)


def _replace_with_symlink(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() and link.resolve() == target.resolve():
        return
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.exists():
        shutil.rmtree(link)
    link.symlink_to(target, target_is_directory=target.is_dir())


def _safe_relative_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"external path must be a non-empty relative path: {value!r}")
    return path


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
