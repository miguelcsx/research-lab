from pydantic import BaseModel, ConfigDict


class Unit(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    symbol: str
    quantity: str
    display: str = ""
    si_multiplier: float = 1.0


def check_unit_compatibility(a: str, b: str) -> bool:
    """Return True if units `a` and `b` measure the same quantity."""
    registry = _default_registry()
    unit_a = registry.get(a.lower())
    unit_b = registry.get(b.lower())
    if unit_a is None or unit_b is None:
        return a.lower() == b.lower()
    return unit_a.quantity == unit_b.quantity


def _default_registry() -> dict[str, Unit]:
    from rlab.units.registry import UnitRegistry
    return UnitRegistry().units
