import inspect
import re
from collections.abc import Callable
from typing import Any

from rlab.constants import EntryKind
from rlab.errors import RegistryError

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

EXPECTED_PARAMETERS = {
    EntryKind.BENCHMARK: 2,
    EntryKind.DATA_SOURCE: 1,
    EntryKind.DATA_TRANSFORM: 2,
    EntryKind.DATA_CHECK: 2,
    EntryKind.DATA_METRIC: 2,
}


def validate_version(version: str) -> str:
    if not SEMVER.fullmatch(version):
        raise RegistryError(f"Invalid semantic version {version!r}")
    return version


def validate_signature(kind: EntryKind, value: Callable[..., Any] | type[Any]) -> None:
    expected = EXPECTED_PARAMETERS.get(kind)
    if expected is None or inspect.isclass(value):
        return
    signature = inspect.signature(value)
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) < expected:
        raise RegistryError(
            f"{kind.value} {value.__qualname__!r} requires at least {expected} parameters"
        )
