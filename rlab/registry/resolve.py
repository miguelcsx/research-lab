from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def resolve_definition(
    value: object,
    expected: type[T],
) -> T:
    result = value() if callable(value) and not isinstance(value, expected) else value
    if not isinstance(result, expected):
        raise TypeError(f"Expected {expected.__name__}, got {type(result).__name__}")
    return result
