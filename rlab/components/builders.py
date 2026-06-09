import inspect
from collections.abc import Mapping
from typing import TypeVar, cast, overload

from rlab.constants import EntryKind
from rlab.references.parser import try_parse_reference
from rlab.registry.store import Registry
from rlab.typing import JsonValue

T = TypeVar("T")


@overload
def build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
) -> object: ...


@overload
def build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
    *,
    expected: type[T],
) -> T: ...


def build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
    *,
    expected: type[T] | None = None,
) -> object | T:
    parsed = try_parse_reference(reference)
    key = str(parsed) if parsed is not None else reference
    record = registry.get(EntryKind.COMPONENT, key)
    value = record.value
    built = value(**dict(params or {})) if inspect.isclass(value) else value
    if expected is not None and not isinstance(built, expected):
        raise TypeError(
            f"Component {reference!r} must be {expected.__name__}, got {type(built).__name__}"
        )
    return cast(T, built) if expected is not None else built


@overload
def try_build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
) -> object | None: ...


@overload
def try_build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
    *,
    expected: type[T],
) -> T | None: ...


def try_build_component(
    registry: Registry,
    reference: str,
    params: Mapping[str, JsonValue] | None = None,
    *,
    expected: type[T] | None = None,
) -> object | T | None:
    parsed = try_parse_reference(reference)
    key = str(parsed) if parsed is not None else reference
    record = registry.try_get(EntryKind.COMPONENT, key)
    if record is None:
        return None
    value = record.value
    built = value(**dict(params or {})) if inspect.isclass(value) else value
    if expected is not None and not isinstance(built, expected):
        raise TypeError(
            f"Component {reference!r} must be {expected.__name__}, got {type(built).__name__}"
        )
    return cast(T, built) if expected is not None else built
