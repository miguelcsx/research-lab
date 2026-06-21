"""Minimal Python host for importing modules and invoking user callables."""

from __future__ import annotations

import json
import os
import sys
import traceback
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from rlab import RuntimeContext
from rlab._rlab import _failed_host_event_line
from rlab._loader import load_modules

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

    ctx = RuntimeContext(
        run_id=request.get("run_id"),
        run_dir=_optional_path(request.get("run_dir")),
        cache_dir=_optional_path(request.get("cache_dir")),
        project_root=_optional_path(request.get("project_root")),
        params_json=json.dumps(request.get("params", {}), sort_keys=True),
        seed=request.get("seed"),
        strict=bool(request.get("strict", False)),
    )
    result = _invoke(project, str(target["kind"]), str(target["name"]), ctx)
    for line in ctx.host_event_lines(str(request["request_id"]), result):
        _write_line(line)


def _invoke(project: Any, kind: str, name: str, ctx: RuntimeContext) -> Any:
    callable_obj = project.resolve(kind, name)
    return callable_obj(ctx)


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
