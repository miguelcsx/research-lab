"""Thin Python decorator ergonomics for rlab declarations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Final, Protocol, TypeVar

T = TypeVar("T")

REF_SEPARATOR: Final = ":"
ATTR_RLAB_REF: Final = "__rlab_ref__"

__all__ = [
    "RegistryProject",
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


def _ref(kind: str, name: str) -> str:
    return f"{kind}{REF_SEPARATOR}{name}"
