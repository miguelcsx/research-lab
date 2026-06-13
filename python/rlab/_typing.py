"""Shared strongly typed contracts for rlab's Python surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Protocol, TypeAlias, TypeVar, cast

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
PathLike: TypeAlias = str | Path

ParamsT = TypeVar("ParamsT", covariant=True)


class SupportsMetricLogging(Protocol):
    def log_metric(self, name: str, value: float) -> None: ...


class ParamsSchema(Protocol[ParamsT]):
    """Minimal schema contract supported by component declarations."""

    @classmethod
    def model_validate(cls, value: object) -> ParamsT: ...

    @classmethod
    def model_json_schema(cls) -> Mapping[str, object]: ...


class JsonSerializable(Protocol):
    def to_dict(self) -> Mapping[str, JsonValue]: ...


def json_object(value: Mapping[str, JsonValue] | None = None) -> JsonObject:
    return dict(value or {})


def json_array(values: Sequence[JsonValue]) -> list[JsonValue]:
    return list(values)


def coerce_json_value(value: object) -> JsonValue:
    """Coerce an arbitrary Python value to a JSON-compatible type."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return coerce_json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(k): coerce_json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [coerce_json_value(item) for item in value]
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return coerce_json_value(cast(Callable[[], object], to_dict)())
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return coerce_json_value(cast(Callable[[], object], model_dump)())
    raise TypeError(f"value is not JSON serializable: {type(value).__name__}")


def coerce_json_object(value: object) -> JsonObject:
    """Coerce an arbitrary mapping to a JSON object."""
    if not isinstance(value, Mapping):
        raise TypeError(f"expected a mapping, got {type(value).__name__}")
    return {str(k): coerce_json_value(v) for k, v in value.items()}


__all__ = [
    "JsonObject",
    "JsonScalar",
    "JsonSerializable",
    "JsonValue",
    "ParamsSchema",
    "ParamsT",
    "PathLike",
    "SupportsMetricLogging",
    "coerce_json_object",
    "coerce_json_value",
    "json_array",
    "json_object",
]
