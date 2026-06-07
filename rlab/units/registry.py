from rlab.units.model import Unit


class UnitRegistry:
    def __init__(self) -> None:
        self.units: dict[str, Unit] = {}
        self._register_defaults()

    def register(self, unit: Unit) -> None:
        self.units[unit.symbol.lower()] = unit
        if unit.display:
            self.units[unit.display.lower()] = unit

    def get(self, symbol: str) -> Unit | None:
        return self.units.get(symbol.lower())

    def _register_defaults(self) -> None:
        defaults = [
            # Time
            Unit(symbol="s", quantity="time", display="seconds"),
            Unit(symbol="ms", quantity="time", display="milliseconds", si_multiplier=1e-3),
            Unit(symbol="min", quantity="time", display="minutes", si_multiplier=60.0),
            Unit(symbol="h", quantity="time", display="hours", si_multiplier=3600.0),
            # Memory
            Unit(symbol="B", quantity="memory", display="bytes"),
            Unit(symbol="KiB", quantity="memory", si_multiplier=1024.0),
            Unit(symbol="MiB", quantity="memory", si_multiplier=1024**2),
            Unit(symbol="GiB", quantity="memory", si_multiplier=1024**3),
            Unit(symbol="KB", quantity="memory", si_multiplier=1000.0),
            Unit(symbol="MB", quantity="memory", si_multiplier=1e6),
            Unit(symbol="GB", quantity="memory", si_multiplier=1e9),
            # Throughput
            Unit(symbol="GB/s", quantity="throughput"),
            Unit(symbol="MB/s", quantity="throughput"),
            Unit(symbol="tokens/s", quantity="throughput"),
            # Energy
            Unit(symbol="J", quantity="energy", display="joules"),
            Unit(symbol="kJ", quantity="energy", si_multiplier=1000.0),
            Unit(symbol="eV", quantity="energy", si_multiplier=1.602e-19),
            # Fraction
            Unit(symbol="%", quantity="fraction", display="percentage"),
            Unit(symbol="dimensionless", quantity="fraction"),
            # Count
            Unit(symbol="count", quantity="count"),
            Unit(symbol="tokens", quantity="count"),
            Unit(symbol="steps", quantity="count"),
            # Temperature
            Unit(symbol="K", quantity="temperature", display="kelvin"),
            Unit(symbol="C", quantity="temperature", display="celsius"),
            # Distance
            Unit(symbol="m", quantity="distance", display="meters"),
            Unit(symbol="nm", quantity="distance", si_multiplier=1e-9),
            Unit(symbol="Å", quantity="distance", si_multiplier=1e-10),
        ]
        for unit in defaults:
            self.register(unit)
