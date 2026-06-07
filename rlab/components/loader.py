from typing import Any

from rlab.components.builders import build_component
from rlab.references.parser import parse_reference
from rlab.registry.store import Registry


def load_component(registry: Registry, value: str) -> Any:
    reference = parse_reference(value)
    return build_component(registry, str(reference))
