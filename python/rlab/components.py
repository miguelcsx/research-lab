"""Native component specifications, requirements, and contracts."""

from __future__ import annotations

from rlab._rlab import (
    ComponentContract,
    ComponentSpec,
    MissingRequirements,
    MissingRequirementsError,
    Requirements,
    collect_component_requirements,
    collect_contracts,
    collect_requirements,
    missing_requirements,
)


def ref(name: str, **params: object) -> ComponentSpec:
    return ComponentSpec(name, params)


__all__ = [
    "ComponentContract",
    "ComponentSpec",
    "MissingRequirements",
    "MissingRequirementsError",
    "Requirements",
    "collect_component_requirements",
    "collect_contracts",
    "collect_requirements",
    "missing_requirements",
    "ref",
]
