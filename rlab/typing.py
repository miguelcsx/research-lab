from collections.abc import Callable, Iterable, Mapping
from typing import Any, TypeAlias

from pydantic import JsonValue

Scalar: TypeAlias = str | int | float | bool | None
MetricValue: TypeAlias = int | float
Metrics: TypeAlias = Mapping[str, MetricValue]
UnitStr: TypeAlias = str
Record: TypeAlias = dict[str, JsonValue]
Records: TypeAlias = Iterable[Record]
Factory: TypeAlias = Any
Serializer: TypeAlias = Callable[[Any], bytes]
Deserializer: TypeAlias = Callable[[bytes], Any]

__all__ = [
    "Deserializer",
    "Factory",
    "JsonValue",
    "MetricValue",
    "Metrics",
    "Record",
    "Records",
    "Scalar",
    "Serializer",
    "UnitStr",
]
