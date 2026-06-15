from __future__ import annotations

import pytest

from rlab import Unit, UnitRegistry
from rlab.units.model import UnitRegistry as ModelUnitRegistry


def test_units_are_rust_backed() -> None:
    registry = UnitRegistry()
    registry.add(Unit("seconds", "s", "time"))

    assert registry.units["s"].name == "seconds"
    assert ModelUnitRegistry().units == {}

    with pytest.raises(ValueError):
        registry.add(Unit("", "bad", "time"))
