import inspect
from typing import Any

from rlab.constants import EntryKind
from rlab.references.parser import parse_reference
from rlab.registry.store import Registry


def build_component(
    registry: Registry, reference: str, params: dict[str, Any] | None = None
) -> Any:
    try:
        parsed = parse_reference(reference)
        key = str(parsed)
    except Exception:
        key = reference
    record = registry.get(EntryKind.COMPONENT, key)
    value = record.value
    if inspect.isclass(value):
        return value(**(params or {}))
    return value
