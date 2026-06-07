from __future__ import annotations

import math
import random
from collections.abc import Callable, Mapping, Sequence
from itertools import product
from typing import Any

from pydantic import JsonValue


# ── core expansion ────────────────────────────────────────────────────────────

def expand_matrix(matrix: Mapping[str, Sequence[JsonValue]]) -> tuple[dict[str, JsonValue], ...]:
    keys = tuple(matrix)
    return tuple(
        dict(zip(keys, values, strict=True)) for values in product(*(matrix[key] for key in keys))
    )


# ── Factor ────────────────────────────────────────────────────────────────────

class Factor:
    """A named experiment dimension with optional metadata."""

    def __init__(
        self,
        name: str,
        values: Sequence[JsonValue],
        *,
        description: str = "",
    ) -> None:
        self.name = name
        self.values = tuple(values)
        self.description = description

    def __repr__(self) -> str:
        return f"Factor({self.name!r}, {self.values!r})"


def factor(name: str, values: Sequence[JsonValue], *, description: str = "") -> Factor:
    """Create a named experiment factor with optional description."""
    return Factor(name, values, description=description)


# ── Grid ──────────────────────────────────────────────────────────────────────

class Grid:
    """Cartesian product of parameter values with optional row filtering."""

    def __init__(self, params: dict[str, Sequence[JsonValue] | Factor]) -> None:
        self._params: dict[str, list[JsonValue]] = {}
        self._descriptions: dict[str, str] = {}
        for key, val in params.items():
            if isinstance(val, Factor):
                self._params[key] = list(val.values)
                self._descriptions[key] = val.description
            else:
                self._params[key] = list(val)

        self._filters: list[Callable[[dict[str, JsonValue]], bool]] = []

    def where(self, predicate: Callable[[Any], bool]) -> "Grid":
        """Filter expanded rows by a predicate function."""
        copy = Grid({})
        copy._params = dict(self._params)
        copy._descriptions = dict(self._descriptions)
        copy._filters = list(self._filters) + [predicate]
        return copy

    def expand(self) -> tuple[dict[str, JsonValue], ...]:
        rows = expand_matrix(self._params)
        for pred in self._filters:
            rows = tuple(r for r in rows if pred(r))
        return rows

    def __len__(self) -> int:
        return len(self.expand())

    def __repr__(self) -> str:
        return f"Grid({self._params!r}, filters={len(self._filters)})"


def grid(params: dict[str, Sequence[JsonValue] | Factor]) -> Grid:
    """Create a Grid from a parameter dict."""
    return Grid(params)


# ── Samplers ──────────────────────────────────────────────────────────────────

class _LogUniform:
    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def sample(self, rng: random.Random | None = None) -> float:
        _rng = rng or random
        return math.exp(_rng.uniform(math.log(self.low), math.log(self.high)))


class _Uniform:
    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def sample(self, rng: random.Random | None = None) -> float:
        _rng = rng or random
        return _rng.uniform(self.low, self.high)


class _Choice:
    def __init__(self, values: Sequence[Any]) -> None:
        self.values = list(values)

    def sample(self, rng: random.Random | None = None) -> Any:
        _rng = rng or random
        return _rng.choice(self.values)


def log_uniform(low: float, high: float) -> _LogUniform:
    return _LogUniform(low, high)


def uniform(low: float, high: float) -> _Uniform:
    return _Uniform(low, high)


def choice(values: Sequence[Any]) -> _Choice:
    return _Choice(values)


class Sample:
    """Random search: sample `n` parameter configurations."""

    def __init__(
        self,
        params: dict[str, _LogUniform | _Uniform | _Choice | Sequence[Any]],
        n: int,
        seed: int | None = None,
    ) -> None:
        self._params = params
        self.n = n
        self.seed = seed

    def expand(self) -> tuple[dict[str, JsonValue], ...]:
        rng = random.Random(self.seed)
        rows: list[dict[str, JsonValue]] = []
        for _ in range(self.n):
            row: dict[str, JsonValue] = {}
            for key, sampler in self._params.items():
                if hasattr(sampler, "sample"):
                    row[key] = sampler.sample(rng)  # type: ignore[assignment]
                else:
                    row[key] = rng.choice(list(sampler))  # type: ignore[arg-type, assignment]
            rows.append(row)
        return tuple(rows)

    def __len__(self) -> int:
        return self.n
