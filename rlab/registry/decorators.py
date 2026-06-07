import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

from rlab.constants import EntryKind
from rlab.registry.namespaces import validate_name
from rlab.registry.records import RegistryRecord
from rlab.registry.store import Registry
from rlab.registry.validation import validate_signature, validate_version

T = TypeVar("T", bound=Callable[..., Any] | type[Any])


def register(  # noqa: PLR0913
    registry: Registry,
    kind: EntryKind,
    name: str,
    value: T,
    *,
    version: str = "1.0.0",
    target_kind: str | None = None,
    tags: tuple[str, ...] = (),
    plugin: str = "project",
) -> T:
    validate_name(name)
    validate_version(version)
    validate_signature(kind, value)
    source = inspect.getsourcefile(cast(Callable[..., Any], value))
    registry.add(
        RegistryRecord(
            kind=kind,
            name=name,
            value=value,
            version=version,
            target_kind=target_kind,
            module=value.__module__,
            qualname=value.__qualname__,
            source=Path(source).resolve() if source else None,
            description=(inspect.getdoc(value) or "").split("\n", maxsplit=1)[0],
            tags=tags,
            plugin=plugin,
        )
    )
    return value
