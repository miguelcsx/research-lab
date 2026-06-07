from __future__ import annotations

from rlab.units.model import Unit, check_unit_compatibility
from rlab.units.registry import UnitRegistry


def test_unit_registry_defaults_and_custom_units() -> None:
    registry = UnitRegistry()
    assert registry.get("s") is not None
    assert registry.get("seconds") is not None
    assert registry.get("MiB") is not None
    assert registry.get("dimensionless") is not None
    assert registry.get("s").quantity == "time"

    registry.register(Unit(symbol="kcal", quantity="energy", si_multiplier=4184.0))
    assert registry.get("kcal").quantity == "energy"


def test_unit_compatibility() -> None:
    assert check_unit_compatibility("s", "ms")
    assert not check_unit_compatibility("s", "MiB")
