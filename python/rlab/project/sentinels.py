"""Declarative sentinel callables and declaration origin introspection."""

from __future__ import annotations

import inspect
import os
from collections.abc import Callable
from pathlib import Path
from typing import cast

from .constants import (
    GENERATED_MODULE,
    QUALNAME_LAMBDA,
    QUALNAME_LOCALS,
    SENTINEL_UNSTABLE_SOURCE_PREFIX,
    STRICT_ENABLED,
    STRICT_ENV_VAR,
)


class WorkflowCallable:
    def __init__(self, name: str) -> None:
        self.__name__ = name
        self.__qualname__ = name
        self.__module__ = GENERATED_MODULE

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeError(
            "workflow sentinels are declarative and are executed by registered workflow steps"
        )


class SentinelCallable:
    def __init__(
        self,
        name: str,
        module: str = GENERATED_MODULE,
        source: str = "",
    ) -> None:
        self.__name__ = name
        self.__qualname__ = name
        self.__module__ = module
        self.__rlab_source__ = source

    def __call__(self, *_args: object, **_kwargs: object) -> None:
        raise RuntimeError("declarative sentinel cannot be executed directly")


def declaration_sentinel(name: str) -> SentinelCallable:
    module, source = declaration_origin()
    return SentinelCallable(name, module=module, source=source)


def declaration_origin() -> tuple[str, str]:
    package_root = Path(__file__).resolve().parents[1]
    frame = inspect.currentframe()

    try:
        while frame is not None:
            frame = frame.f_back
            if frame is None:
                return GENERATED_MODULE, ""

            source = Path(frame.f_code.co_filename).resolve()
            if source != package_root and package_root not in source.parents:
                return str(frame.f_globals.get("__name__", "")), str(source)
    finally:
        del frame

    return GENERATED_MODULE, ""


def object_origin(obj: object) -> tuple[str, str, str]:
    module = str(getattr(obj, "__module__", ""))
    qualname = str(getattr(obj, "__qualname__", getattr(obj, "__name__", "")))
    declared_source = getattr(obj, "__rlab_source__", "")

    if declared_source:
        return module, qualname, str(declared_source)

    source = source_file(obj) if callable(obj) or isinstance(obj, type) else ""
    return module, qualname, source


def source_file(obj: object) -> str:
    try:
        return (
            inspect.getsourcefile(cast(Callable[..., object] | type[object], obj)) or ""
        )
    except (TypeError, OSError):
        return ""


def strict_unstable_declaration(*, obj: object, qualname: str, source: str) -> bool:
    if os.environ.get(STRICT_ENV_VAR) != STRICT_ENABLED:
        return False

    if isinstance(obj, SentinelCallable | WorkflowCallable):
        return False

    return (
        not source
        or source.startswith(SENTINEL_UNSTABLE_SOURCE_PREFIX)
        or QUALNAME_LAMBDA in qualname
        or QUALNAME_LOCALS in qualname
    )
