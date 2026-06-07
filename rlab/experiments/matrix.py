from collections.abc import Mapping, Sequence
from itertools import product

from pydantic import JsonValue


def expand_matrix(matrix: Mapping[str, Sequence[JsonValue]]) -> tuple[dict[str, JsonValue], ...]:
    keys = tuple(matrix)
    return tuple(
        dict(zip(keys, values, strict=True)) for values in product(*(matrix[key] for key in keys))
    )
