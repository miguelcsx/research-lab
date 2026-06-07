from collections.abc import Mapping, Sequence

from pydantic import JsonValue

from rlab.experiments.matrix import expand_matrix


def sweep(matrix: Mapping[str, Sequence[JsonValue]]) -> tuple[dict[str, JsonValue], ...]:
    return expand_matrix(matrix)
