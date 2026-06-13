"""Thin Python decorator ergonomics for rlab declarations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, Protocol, TypeVar

T = TypeVar("T")

ACTION_KEEP: Final = "keep"
ACTION_UPDATE: Final = "update"
ACTION_DROP: Final = "drop"
ACTION_BOUNDARY: Final = "boundary"

REF_SEPARATOR: Final = ":"
ATTR_RLAB_REF: Final = "__rlab_ref__"

__all__ = [
    "ComponentUse",
    "DataDecision",
    "RegistryProject",
    "data_boundary",
    "data_drop",
    "data_keep",
    "data_update",
    "decorator_factory",
]


class RegistryProject(Protocol):
    def _register(
        self,
        *,
        kind: str,
        name: str,
        obj: object,
        metadata: dict[str, object],
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ComponentUse:
    """Reference to a registered component-like object."""

    ref: str


@dataclass(frozen=True, slots=True)
class DataDecision:
    """Typed data decision emitted by data helpers."""

    action: str
    record: object | None = None
    reason: str | None = None
    kind: str | None = None


def data_keep(record: object) -> DataDecision:
    """Keep a record unchanged."""
    return _decision(ACTION_KEEP, record=record)


def data_update(record: object, reason: str | None = None) -> DataDecision:
    """Keep an updated record."""
    return _decision(ACTION_UPDATE, record=record, reason=reason)


def data_drop(reason: str) -> DataDecision:
    """Drop a record with a reason."""
    return _decision(ACTION_DROP, reason=reason)


def data_boundary(value: object, kind: str) -> DataDecision:
    """Emit a boundary value for later batch-level processing."""
    return _decision(ACTION_BOUNDARY, record=value, kind=kind)


def decorator_factory(
    project: RegistryProject,
    kind: str,
    name: str,
    metadata: dict[str, object],
) -> Callable[[T], T]:
    """Create a normal Python decorator that records declaration metadata."""
    ref = _ref(kind, name)
    metadata_snapshot = dict(metadata)

    def decorate(obj: T) -> T:
        if isinstance(obj, type):
            setattr(obj, ATTR_RLAB_REF, ref)

        project._register(
            kind=kind,
            name=name,
            obj=obj,
            metadata=dict(metadata_snapshot),
        )
        return obj

    return decorate


def _decision(
    action: str,
    *,
    record: object | None = None,
    reason: str | None = None,
    kind: str | None = None,
) -> DataDecision:
    return DataDecision(action=action, record=record, reason=reason, kind=kind)


def _ref(kind: str, name: str) -> str:
    return f"{kind}{REF_SEPARATOR}{name}"
