import inspect
from typing import Any

from rlab.constants import EntryKind
from rlab.registry.store import Registry


def build_component(
    registry: Registry, reference: str, params: dict[str, Any] | None = None
) -> Any:
    record = registry.get(EntryKind.COMPONENT, reference)
    value = record.value
    if inspect.isclass(value):
        return value(**(params or {}))
    return value
