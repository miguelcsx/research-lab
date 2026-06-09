import inspect
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from rlab.constants import EntryKind
from rlab.registry.namespaces import validate_name
from rlab.registry.records import RegistryRecord
from rlab.registry.store import Registry
from rlab.registry.validation import validate_signature, validate_version

T = TypeVar("T")


def register(  # noqa: PLR0913
    registry: Registry,
    kind: EntryKind,
    name: str,
    value: T,
    *,
    version: str = "1.0.0",
    target_kind: str | None = None,
    tags: tuple[str, ...] = (),
    package: str = "project",
    declared_by: Callable[..., object] | type[object] | None = None,
) -> T:
    validate_name(name)
    validate_version(version)
    validate_signature(kind, value)
    declaration = declared_by or (
        cast(Callable[..., object] | type[object], value) if callable(value) else None
    )
    source = inspect.getsourcefile(declaration) if declaration is not None else None
    module = declaration.__module__ if declaration is not None else type(value).__module__
    qualname = declaration.__qualname__ if declaration is not None else type(value).__qualname__
    description = inspect.getdoc(declaration or value) or ""
    registry.add(
        RegistryRecord(
            kind=kind,
            name=name,
            value=value,
            version=version,
            target_kind=target_kind,
            module=module,
            qualname=qualname,
            source=Path(source).resolve() if source else None,
            description=description.split("\n", maxsplit=1)[0],
            tags=tags,
            package=package,
        )
    )
    return value
