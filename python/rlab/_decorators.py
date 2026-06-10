"""Thin Python decorator ergonomics for rlab declarations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class ComponentUse:
    """Reference to a registered component-like object."""

    ref: str


@dataclass(frozen=True, slots=True)
class DataDecision:
    """Typed data decision emitted by data helpers."""

    action: str
    record: Any | None = None
    reason: str | None = None
    kind: str | None = None


def data_keep(record: Mapping[str, Any]) -> DataDecision:
    """Keep a record unchanged."""
    return DataDecision(action="keep", record=dict(record))


def data_update(record: Mapping[str, Any], reason: str | None = None) -> DataDecision:
    """Keep an updated record."""
    return DataDecision(action="update", record=dict(record), reason=reason)


def data_drop(reason: str) -> DataDecision:
    """Drop a record with a reason."""
    return DataDecision(action="drop", reason=reason)


def data_boundary(value: Any, kind: str) -> DataDecision:
    """Emit a boundary value for later batch-level processing."""
    return DataDecision(action="boundary", record=value, kind=kind)


def decorator_factory(project: Any, kind: str, name: str, metadata: dict[str, Any]) -> Callable[[Any], Any]:
    """Create a normal Python decorator that records declaration metadata."""

    def decorate(obj: Any) -> Any:
        project._register(kind=kind, name=name, obj=obj, metadata=metadata)
        return obj

    return decorate
