from __future__ import annotations

import pytest

from rlab.units import Unit, UnitRegistry


def test_units_are_rust_backed() -> None:
    registry = UnitRegistry()
    registry.add(Unit("seconds", "s", "time"))

    assert registry.units["s"].name == "seconds"
    assert UnitRegistry().units == {}

    with pytest.raises(ValueError):
        registry.add(Unit("", "bad", "time"))
