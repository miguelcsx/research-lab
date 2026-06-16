"""Minimal Python host for importing modules and invoking user callables."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import traceback
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from rlab import RuntimeContext
from rlab._rlab import _failed_host_event_line, execute_dataset
from rlab._loader import load_modules
from rlab.components import ComponentSpec
from rlab.refs import ArtifactRef, RunRef

PROTOCOL_VERSION = 1
SCHEMA_VERSION = 1
STRICT_ENV_VAR = "RLAB_STRICT"


def main() -> int:
    request_id = "unknown"
    try:
        request = _read_request()
        request_id = str(request["request_id"])
        os.environ[STRICT_ENV_VAR] = "1" if request.get("strict") else "0"
        project = load_modules(
            request["project_root"],
            request.get("modules", []),
            strict=bool(request.get("strict", False)),
        )
        for record in project.records:
            _emit(request, "registry_record", record=record)
        if request.get("command") == "execute":
            _execute(request, project)
        else:
            _emit_completed(request, {"ok": True})
    except Exception as exc:  # noqa: BLE001 - host boundary must report all failures.
        _write_line(
            _failed_host_event_line(
                request_id,
                "python_exception",
                f"{type(exc).__name__}: {exc}",
                traceback.format_exc(),
                "rlab._runner",
            )
        )
    return 0


def _read_request() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise ValueError("runner received no request")
    request = json.loads(line)
    if request.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version: {request.get('protocol_version')}")
    return cast(dict[str, Any], request)


def _execute(request: Mapping[str, Any], project: Any) -> None:
    target = request.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("execute request requires a target")

    base_ctx = RuntimeContext(
        run_id=request.get("run_id"),
        run_dir=_optional_path(request.get("run_dir")),
        cache_dir=_optional_path(request.get("cache_dir")),
        project_root=_optional_path(request.get("project_root")),
        params_json=json.dumps(request.get("params", {}), sort_keys=True),
        seed=request.get("seed"),
    )
    ctx = _ChildContext(base_ctx)
    result = _invoke(project, str(target["kind"]), str(target["name"]), cast(RuntimeContext, ctx))
    ctx.save_children()
    for line in base_ctx.host_event_lines(str(request["request_id"]), result):
        _write_line(line)


class _ChildContext:
    def __init__(self, base: RuntimeContext) -> None:
        self._base = base
        self._children: list[dict[str, str]] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._base, name)

    def run(self, target: str, params: Mapping[str, object] | None = None) -> RunRef:
        command = _child_command(Path(self._base.project_root), target, params or {})
        result = subprocess.run(
            command,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        payload = json.loads(result.stdout)
        data = _run_data(payload, Path(self._base.project_root))
        ref = RunRef(
            id=str(data["id"]),
            target=target,
            path=Path(str(data["path"])),
        )
        self._children.append(
            {"id": ref.id, "target": ref.target, "path": str(ref.path)}
        )
        return ref

    def save_children(self) -> None:
        if not self._children:
            return
        path = Path(self._base.output_path(Path("children.json")))
        path.write_text(
            json.dumps(self._children, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self._base.save_artifact("run.children", path, kind="file")


def _child_command(
    root: Path,
    target: str,
    params: Mapping[str, object],
) -> list[str]:
    if target.startswith("dataset:"):
        command = [sys.executable, "-m", "rlab", "--root", str(root), "data", "build", target, "--json"]
        for key, value in params.items():
            command.extend(["--override", f"{key}={_param_value(value)}"])
        return command
    command = [sys.executable, "-m", "rlab", "--root", str(root), "run", target, "--json"]
    for key, value in params.items():
        command.extend(["--param", f"{key}={_param_value(value)}"])
    return command


def _param_value(value: object) -> str:
    if isinstance(value, ArtifactRef):
        return str(value.path)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, str | int | float | bool):
        return str(value)
    return json.dumps(_jsonable(value), sort_keys=True)


def _run_data(payload: Mapping[str, object], root: Path) -> Mapping[str, object]:
    data = payload.get("data")
    if not isinstance(data, Mapping):
        raise ValueError("child run returned invalid JSON")
    if "id" in data:
        return data
    runs = data.get("runs")
    if isinstance(runs, list) and len(runs) == 1:
        run_id = str(runs[0])
        return {
            "id": run_id,
            "path": str(root / ".rlab" / "runs" / run_id),
        }
    raise ValueError("ctx.run expected exactly one child run")


def _invoke(project: Any, kind: str, name: str, ctx: RuntimeContext) -> Any:
    if kind == "workflow":
        return _invoke_workflow(project, name, ctx)
    if kind == "dataset":
        return _invoke_dataset(project, name, ctx)

    callable_obj = project.resolve(kind, name)
    target_ref = _params(ctx).get("target")
    if isinstance(target_ref, str) and target_ref:
        return callable_obj(_resolve_component(project, target_ref, "loader"), ctx)
    return callable_obj(ctx)


def _invoke_workflow(project: Any, name: str, ctx: RuntimeContext) -> dict[str, Any]:
    record = project.record("workflow", name)
    steps = record.get("metadata", {}).get("steps", [])
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"workflow has no steps: {name}")
    return {
        "workflow": name,
        "steps": [
            _invoke_workflow_step(project, ctx, name, step, index)
            for index, step in enumerate(steps)
        ],
    }


def _invoke_workflow_step(
    project: Any,
    ctx: RuntimeContext,
    workflow: str,
    step: object,
    index: int,
) -> dict[str, Any]:
    if not isinstance(step, Mapping):
        raise ValueError("workflow step metadata must be an object")
    name = str(step.get("name", f"step_{index}"))
    callable_obj = project.resolve("workflow_step", f"{workflow}:{name}")
    return {"name": name, "index": index, "result": _jsonable(callable_obj(ctx))}


def _invoke_dataset(project: Any, name: str, ctx: RuntimeContext) -> dict[str, Any]:
    metadata = _metadata(project.record("dataset", name))
    if "source" not in metadata and "pipeline" not in metadata:
        return cast(dict[str, Any], _jsonable(project.resolve("dataset", name)(ctx)))

    ctx.report_progress("dataset", name, "running", 0, None, "building dataset")
    result = cast(
        dict[str, Any],
        json.loads(
            execute_dataset(
                name,
                _dataset_source(project, name, metadata),
                _dataset_stages(project, metadata),
                _dataset_sinks(project, name, metadata),
                ctx,
            )
        ),
    )
    records = result.get("records", 0)
    ctx.report_progress("dataset", name, "completed", records, None, f"{records} records")
    return result


def _dataset_source(project: Any, name: str, metadata: Mapping[str, Any]) -> Any:
    try:
        return _materialize(project.resolve("dataset_source", name))
    except KeyError:
        return _resolve_component(project, metadata.get("source"), "source")


def _dataset_stages(
    project: Any,
    metadata: Mapping[str, Any],
) -> list[tuple[str, Any, dict[str, Any]]]:
    ref = _component_spec(metadata.get("pipeline"), "pipeline").ref
    pipeline = project.record("pipeline", ref.split(":", 1)[1])
    stages = _metadata(pipeline).get("stages", [])
    if not isinstance(stages, list):
        return []
    return [_dataset_stage(project, stage) for stage in stages]


def _dataset_stage(project: Any, value: object) -> tuple[str, Any, dict[str, Any]]:
    spec = _component_spec(value, "transform")
    params = spec.params if isinstance(spec.params, dict) else {}
    return spec.ref, project.build_spec(spec), params


def _dataset_sinks(project: Any, name: str, metadata: Mapping[str, Any]) -> list[Any]:
    bound = []
    index = 0
    while True:
        try:
            bound.append(project.resolve("dataset_sink", f"{name}:{index}"))
        except KeyError:
            break
        index += 1
    if bound:
        return bound
    sinks = metadata.get("sinks", [])
    if not isinstance(sinks, list):
        sinks = [sinks]
    return [_resolve_component(project, sink, "sink") for sink in sinks]


def _resolve_component(project: Any, value: object, default_kind: str) -> Any:
    spec = _component_spec(value, default_kind)
    reference = spec.ref
    kind, rest = reference.split(":", 1)
    if ":" in rest:
        loader_name, path = rest.split(":", 1)
        loader = _materialize(project.resolve("loader", loader_name))
        load = getattr(loader, "load", None)
        if not callable(load):
            raise ValueError(f"loader has no load(path): {loader_name}")
        return load(path)
    return project.build_spec(spec)


def _component_spec(value: object, default_kind: str) -> ComponentSpec[dict[str, Any]]:
    spec = ComponentSpec.from_value(_component_payload(value, default_kind))
    ref = spec.ref if ":" in spec.ref else f"{default_kind}:{spec.ref}"
    return ComponentSpec(ref=ref, params=spec.params)


def _component_payload(value: object, default_kind: str) -> object:
    if isinstance(value, str):
        return value if ":" in value else f"{default_kind}:{value}"
    if isinstance(value, Mapping):
        ref = value.get("ref") or value.get("reference") or value.get("name")
        if isinstance(ref, str) and ref:
            normalized = ref if ":" in ref else f"{default_kind}:{ref}"
            return {**value, "ref": normalized}
    return value


def _metadata(record: Mapping[str, Any]) -> Mapping[str, Any]:
    metadata = record.get("metadata", {})
    if not isinstance(metadata, Mapping):
        raise TypeError("registry metadata must be an object")
    return metadata


def _materialize(value: Any) -> Any:
    if isinstance(value, type):
        return value()
    return value


def _emit_completed(request: Mapping[str, Any], data: object) -> None:
    _emit(
        request,
        "completed",
        result={"schema_version": SCHEMA_VERSION, "data": _jsonable(data)},
    )


def _emit(request: Mapping[str, Any], event_type: str, **fields: object) -> None:
    _emit_raw(
        {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": request["request_id"],
            "event_type": event_type,
            **fields,
        }
    )


def _emit_raw(event: Mapping[str, object]) -> None:
    _write_line(json.dumps(event, separators=(",", ":"), sort_keys=True))


def _write_line(line: str) -> None:
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _jsonable(value: object) -> object:
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _jsonable(to_dict())
    to_json = getattr(value, "to_json", None)
    if callable(to_json):
        return json.loads(to_json())
    return str(value)


def _params(ctx: RuntimeContext) -> Mapping[str, object]:
    raw = getattr(ctx, "params_json", None)
    return json.loads(raw()) if callable(raw) else {}


def _optional_path(value: object) -> Path | None:
    return None if value is None else Path(str(value))


if __name__ == "__main__":
    raise SystemExit(main())
