from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def resolve_definition(
    value: Callable[..., object] | type[object],
    expected: type[T],
) -> T:
    result = value() if callable(value) and not inspect.isclass(value) else value
    if not isinstance(result, expected):
        raise TypeError(f"Expected {expected.__name__}, got {type(result).__name__}")
    return result
