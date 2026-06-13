"""Runner JSON, typing, and callable serialization helpers."""

from __future__ import annotations

import inspect
import json
import math
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import TypeGuard, cast

from rlab._typing import JsonObject, JsonValue

from .constants import (
    ENCODING,
    ERROR_MAPPING,
    ERROR_NUMERIC,
    JSON_INDENT,
    JSON_NEWLINE,
)


def is_finite_number(value: object) -> TypeGuard[int | float]:
    return (
        not isinstance(value, bool)
        and isinstance(value, int | float)
        and math.isfinite(float(value))
    )


def jsonable(value: object) -> JsonValue:
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int | float):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return jsonable(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(item) for item in value]

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return jsonable(cast(Callable[[], object], to_dict)())

    return repr(value)


def mapping_value(value: object, label: str) -> Mapping[str, JsonValue]:
    if not isinstance(value, Mapping):
        raise TypeError(ERROR_MAPPING.format(label=label))
    return {str(key): jsonable(item) for key, item in value.items()}


def number_value(value: object, label: str) -> int | float:
    if not isinstance(value, bool) and isinstance(value, int | float):
        return value
    raise TypeError(ERROR_NUMERIC.format(label=label))


def pretty_json(value: object) -> str:
    return json.dumps(value, indent=JSON_INDENT, sort_keys=True) + JSON_NEWLINE


def write_pretty_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pretty_json(value), encoding=ENCODING)


def call_with_optional_context(callable_obj: object, *args: object) -> object:
    function = cast(Callable[..., object], callable_obj)
    if accepts_args(function, args):
        return function(*args)
    if not args:
        return function()
    return function(*args[:-1])


def accepts_args(function: Callable[..., object], args: tuple[object, ...]) -> bool:
    try:
        inspect.signature(function).bind(*args)
    except TypeError:
        return False
    return True
