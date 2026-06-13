"""Shared strongly typed contracts for rlab's Python surface."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Protocol, TypeAlias, TypeVar

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


__all__ = [
    "JsonObject",
    "JsonScalar",
    "JsonSerializable",
    "JsonValue",
    "ParamsSchema",
    "ParamsT",
    "PathLike",
    "SupportsMetricLogging",
    "json_array",
    "json_object",
]
