"""Versioned JSONL protocol helpers for the Python runner."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, cast

from ._typing import JsonObject, JsonValue, coerce_json_object, coerce_json_value

PROTOCOL_VERSION: Final = 1

Command: TypeAlias = Literal["discover", "validate_imports", "execute"]

COMMAND_DISCOVER: Final = "discover"
COMMAND_VALIDATE_IMPORTS: Final = "validate_imports"
COMMAND_EXECUTE: Final = "execute"
SUPPORTED_COMMANDS: Final[frozenset[str]] = frozenset(
    (COMMAND_DISCOVER, COMMAND_VALIDATE_IMPORTS, COMMAND_EXECUTE)
)

KEY_PROTOCOL_VERSION: Final = "protocol_version"
KEY_REQUEST_ID: Final = "request_id"
KEY_COMMAND: Final = "command"
KEY_PROJECT_ROOT: Final = "project_root"
KEY_MODULES: Final = "modules"
KEY_TARGET: Final = "target"
KEY_KIND: Final = "kind"
KEY_NAME: Final = "name"
KEY_RUN_ID: Final = "run_id"
KEY_RUN_DIR: Final = "run_dir"
KEY_CACHE_DIR: Final = "cache_dir"
KEY_PARAMS: Final = "params"
KEY_SEED: Final = "seed"
KEY_STRICT: Final = "strict"
KEY_ENVIRONMENT: Final = "environment"
KEY_EVENT_TYPE: Final = "event_type"

DEFAULT_PROTOCOL_VERSION: Final = 0
DEFAULT_MODULES: Final = ()
DEFAULT_PARAMS: Final[JsonObject] = {}
DEFAULT_ENVIRONMENT: Final[JsonObject] = {}
DEFAULT_STRICT: Final = False

JSON_SEPARATORS: Final = (",", ":")


@dataclass(frozen=True, slots=True)
class HostTarget:
    kind: str
    name: str


@dataclass(frozen=True, slots=True)
class HostRequest:
    protocol_version: int
    request_id: str
    command: Command
    project_root: str
    modules: list[str]
    target: HostTarget | None
    run_id: str | None
    run_dir: str | None
    cache_dir: str | None
    params: JsonObject
    seed: int | None
    strict: bool
    environment: JsonObject


def read_request() -> HostRequest:
    """Read one JSON request from stdin and validate its outer shape."""
    line = sys.stdin.readline()
    if not line:
        raise ValueError("runner received no request")

    raw = coerce_json_object(json.loads(line))
    version = _required_int(
        raw.get(KEY_PROTOCOL_VERSION, DEFAULT_PROTOCOL_VERSION),
        KEY_PROTOCOL_VERSION,
    )
    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version: {version}")

    command = _command(raw[KEY_COMMAND])
    modules = _string_list(raw.get(KEY_MODULES, DEFAULT_MODULES), KEY_MODULES)
    seed = _optional_int(raw.get(KEY_SEED), KEY_SEED)

    return HostRequest(
        protocol_version=version,
        request_id=str(raw[KEY_REQUEST_ID]),
        command=command,
        project_root=str(raw[KEY_PROJECT_ROOT]),
        modules=modules,
        target=_target(raw.get(KEY_TARGET)),
        run_id=_optional_str(raw.get(KEY_RUN_ID)),
        run_dir=_optional_str(raw.get(KEY_RUN_DIR)),
        cache_dir=_optional_str(raw.get(KEY_CACHE_DIR)),
        params=coerce_json_object(raw.get(KEY_PARAMS, DEFAULT_PARAMS)),
        seed=seed,
        strict=bool(raw.get(KEY_STRICT, DEFAULT_STRICT)),
        environment=coerce_json_object(raw.get(KEY_ENVIRONMENT, DEFAULT_ENVIRONMENT)),
    )


def emit_event(event: JsonObject) -> None:
    """Write one protocol event as JSONL."""
    event.setdefault(KEY_PROTOCOL_VERSION, PROTOCOL_VERSION)
    sys.stdout.write(
        json.dumps(event, separators=JSON_SEPARATORS, sort_keys=True) + "\n"
    )
    sys.stdout.flush()


def base_event(request: HostRequest, event_type: str) -> JsonObject:
    return {
        KEY_PROTOCOL_VERSION: PROTOCOL_VERSION,
        KEY_REQUEST_ID: request.request_id,
        KEY_EVENT_TYPE: event_type,
    }


def _target(value: object) -> HostTarget | None:
    if value is None:
        return None

    target = coerce_json_object(value)
    return HostTarget(kind=str(target[KEY_KIND]), name=str(target[KEY_NAME]))


def _command(value: object) -> Command:
    if not isinstance(value, str):
        raise TypeError("command must be a string")

    if value not in SUPPORTED_COMMANDS:
        raise ValueError(f"unsupported runner command: {value!r}")

    return cast(Command, value)


def _required_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{label} must be an integer")
    return value


def _optional_int(value: object, label: str) -> int | None:
    if value is None:
        return None
    return _required_int(value, label)


def _optional_str(value: object) -> str | None:
    return None if value is None else str(value)


def _string_list(value: object, label: str) -> list[str]:
    if not isinstance(value, list | tuple):
        raise TypeError(f"{label} must be a list")
    return [str(item) for item in value]


