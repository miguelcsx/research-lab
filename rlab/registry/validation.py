import inspect
import re
from collections.abc import Callable
from typing import Any, cast

from rlab.constants import EntryKind
from rlab.errors import RegistryError

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

# Callables may receive (target) or (target, ctx) — ctx is optional.
MIN_PARAMETERS = {
    EntryKind.BENCHMARK: 1,
}


def validate_version(version: str) -> str:
    if not SEMVER.fullmatch(version):
        raise RegistryError(f"Invalid semantic version {version!r}")
    return version


def validate_signature(kind: EntryKind, value: object) -> None:
    minimum = MIN_PARAMETERS.get(kind)
    if minimum is None or inspect.isclass(value) or not callable(value):
        return
    function = cast(Callable[..., Any], value)
    signature = inspect.signature(function)
    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    if len(positional) < minimum:
        raise RegistryError(
            f"{kind.value} {function.__qualname__!r} requires at least {minimum} parameter(s)"
        )
