"""Versioned JSONL protocol helpers for the Python runner."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import Any, Literal

PROTOCOL_VERSION = 1


@dataclass(frozen=True, slots=True)
class HostTarget:
    kind: str
    name: str


@dataclass(frozen=True, slots=True)
class HostRequest:
    protocol_version: int
    request_id: str
    command: Literal["discover", "validate_imports", "execute"]
    project_root: str
    modules: list[str]
    target: HostTarget | None
    run_id: str | None
    run_dir: str | None
    cache_dir: str | None
    params: dict[str, Any]
    seed: int | None
    strict: bool
    environment: dict[str, Any]


def read_request() -> HostRequest:
    """Read one JSON request from stdin and validate its outer shape."""
    line = sys.stdin.readline()
    if not line:
        raise ValueError("runner received no request")
    raw = json.loads(line)
    version = int(raw.get("protocol_version", 0))
    if version != PROTOCOL_VERSION:
        raise ValueError(f"unsupported protocol version: {version}")
    target_raw = raw.get("target")
    target = (
        None
        if target_raw is None
        else HostTarget(kind=str(target_raw["kind"]), name=str(target_raw["name"]))
    )
    return HostRequest(
        protocol_version=version,
        request_id=str(raw["request_id"]),
        command=raw["command"],
        project_root=str(raw["project_root"]),
        modules=[str(module) for module in raw.get("modules", [])],
        target=target,
        run_id=None if raw.get("run_id") is None else str(raw["run_id"]),
        run_dir=None if raw.get("run_dir") is None else str(raw["run_dir"]),
        cache_dir=None if raw.get("cache_dir") is None else str(raw["cache_dir"]),
        params=dict(raw.get("params", {})),
        seed=raw.get("seed"),
        strict=bool(raw.get("strict", False)),
        environment=dict(raw.get("environment", {})),
    )


def emit_event(event: dict[str, Any]) -> None:
    """Write one protocol event as JSONL."""
    event.setdefault("protocol_version", PROTOCOL_VERSION)
    sys.stdout.write(json.dumps(event, separators=(",", ":"), sort_keys=True) + "\n")
    sys.stdout.flush()


def base_event(request: HostRequest, event_type: str) -> dict[str, Any]:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "request_id": request.request_id,
        "event_type": event_type,
    }
