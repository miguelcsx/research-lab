from collections.abc import Iterable, Mapping
from typing import Any, TypeAlias

from pydantic import JsonValue

Scalar: TypeAlias = str | int | float | bool | None
Metrics: TypeAlias = Mapping[str, int | float]
Record: TypeAlias = dict[str, JsonValue]
Records: TypeAlias = Iterable[Record]
Factory: TypeAlias = Any

__all__ = ["Factory", "JsonValue", "Metrics", "Record", "Records", "Scalar"]
