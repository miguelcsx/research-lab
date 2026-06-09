from collections.abc import Iterable, Mapping
from typing import Any, Protocol, TypeAlias, TypeVar

from pydantic import JsonValue

Scalar: TypeAlias = str | int | float | bool | None
MetricValue: TypeAlias = int | float
Metrics: TypeAlias = Mapping[str, MetricValue]
UnitStr: TypeAlias = str
Record: TypeAlias = dict[str, JsonValue]
Records: TypeAlias = Iterable[Record]
JsonObject: TypeAlias = dict[str, JsonValue]
JsonMapping: TypeAlias = Mapping[str, JsonValue]
Factory: TypeAlias = Any
T_contra = TypeVar("T_contra", contravariant=True)
T_co = TypeVar("T_co", covariant=True)


class Serializer(Protocol[T_contra]):
    def __call__(self, value: T_contra) -> bytes: ...


class Deserializer(Protocol[T_co]):
    def __call__(self, value: bytes) -> T_co: ...


__all__ = [
    "Deserializer",
    "Factory",
    "JsonMapping",
    "JsonObject",
    "JsonValue",
    "MetricValue",
    "Metrics",
    "Record",
    "Records",
    "Scalar",
    "Serializer",
    "UnitStr",
]
