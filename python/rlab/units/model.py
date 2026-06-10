"""Unit helpers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Unit:
    name: str
    symbol: str
    dimension: str


@dataclass(slots=True)
class UnitRegistry:
    units: dict[str, Unit] = field(default_factory=dict)

    def add(self, unit: Unit) -> None:
        if not unit.name or not unit.symbol or not unit.dimension:
            raise ValueError("unit name, symbol, and dimension are required")
        self.units[unit.symbol] = unit
