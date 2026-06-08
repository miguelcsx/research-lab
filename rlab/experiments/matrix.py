from __future__ import annotations

import math
import random
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from itertools import product
from typing import Any

from pydantic import JsonValue


def expand_matrix(matrix: Mapping[str, Sequence[JsonValue]]) -> tuple[dict[str, JsonValue], ...]:
    keys = tuple(matrix)
    return tuple(
        dict(zip(keys, values, strict=True)) for values in product(*(matrix[key] for key in keys))
    )


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

    def where(self, predicate: Callable[[Any], bool]) -> Grid:
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


class _Sampler(ABC):
    """Base class for objects that can be sampled."""

    @abstractmethod
    def sample(self, rng: random.Random | None = None) -> Any: ...


class _LogUniform(_Sampler):
    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def sample(self, rng: random.Random | None = None) -> float:
        _rng = rng or random
        return math.exp(_rng.uniform(math.log(self.low), math.log(self.high)))


class _Uniform(_Sampler):
    def __init__(self, low: float, high: float) -> None:
        self.low = low
        self.high = high

    def sample(self, rng: random.Random | None = None) -> float:
        _rng = rng or random
        return _rng.uniform(self.low, self.high)


class _Choice(_Sampler):
    def __init__(self, values: Sequence[Any]) -> None:
        self.values = list(values)

    def sample(self, rng: random.Random | None = None) -> Any:
        _rng = rng or random
        return _rng.choice(self.values)


class _SequenceSampler(_Sampler):
    """Wraps a sequence as a sampler."""

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
        self._params = self._normalize_params(params)
        self.n = n
        self.seed = seed

    @staticmethod
    def _normalize_params(
        params: dict[str, _LogUniform | _Uniform | _Choice | Sequence[Any]],
    ) -> dict[str, _Sampler]:
        """Convert all parameter values to samplers."""
        normalized: dict[str, _Sampler] = {}
        for key, value in params.items():
            if isinstance(value, _Sampler):
                normalized[key] = value
            else:
                # It's a Sequence, wrap it as a sampler
                normalized[key] = _SequenceSampler(value)
        return normalized

    def expand(self) -> tuple[dict[str, JsonValue], ...]:
        rng = random.Random(self.seed)
        rows: list[dict[str, JsonValue]] = []
        for _ in range(self.n):
            row: dict[str, JsonValue] = {}
            for key, sampler in self._params.items():
                row[key] = sampler.sample(rng)
            rows.append(row)
        return tuple(rows)

    def __len__(self) -> int:
        return self.n
