import inspect
from typing import Any

from rlab.constants import EntryKind
from rlab.references.parser import try_parse_reference
from rlab.registry.store import Registry


def build_component(
    registry: Registry, reference: str, params: dict[str, Any] | None = None
) -> Any:
    parsed = try_parse_reference(reference)
    key = str(parsed) if parsed is not None else reference
    record = registry.get(EntryKind.COMPONENT, key)
    value = record.value
    if inspect.isclass(value):
        return value(**(params or {}))
    return value


def try_build_component(
    registry: Registry, reference: str, params: dict[str, Any] | None = None
) -> Any | None:
    parsed = try_parse_reference(reference)
    key = str(parsed) if parsed is not None else reference
    record = registry.try_get(EntryKind.COMPONENT, key)
    if record is None:
        return None
    value = record.value
    if inspect.isclass(value):
        return value(**(params or {}))
    return value
