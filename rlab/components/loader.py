from typing import TypeVar, overload

from rlab.components.builders import build_component
from rlab.references.parser import parse_reference
from rlab.registry.store import Registry

T = TypeVar("T")


@overload
def load_component(registry: Registry, value: str) -> object: ...


@overload
def load_component(registry: Registry, value: str, *, expected: type[T]) -> T: ...


def load_component(
    registry: Registry,
    value: str,
    *,
    expected: type[T] | None = None,
) -> object | T:
    reference = parse_reference(value)
    if expected is None:
        return build_component(registry, str(reference))
    return build_component(registry, str(reference), expected=expected)
