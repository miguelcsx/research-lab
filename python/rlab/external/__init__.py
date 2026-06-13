"""External command descriptors for rlab."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from rlab._typing import JsonValue

PATH_PARENT: Final = ".."
DEFAULT_WORKSPACE_IGNORED: Final[tuple[str, ...]] = ()
DEFAULT_EXTERNAL_PATHS: Final[tuple["ExternalPath", ...]] = ()
DEFAULT_ARTIFACTS: Final[tuple[str, ...]] = ()

ERROR_EXTERNAL_PATH: Final = "external path"
ERROR_MANAGED_PATH_NAME: Final = "managed path name"
ERROR_ARTIFACT_PATTERN: Final = "artifact pattern"
ERROR_SOURCE_PARAM_EMPTY: Final = "workspace source_param cannot be empty"
ERROR_DEFAULT_SOURCE_EMPTY: Final = "workspace default_source cannot be empty"
ERROR_WORKSPACE_PATHS_UNIQUE: Final = "workspace paths must be unique"
ERROR_CACHED_NAMES_UNIQUE: Final = "cached path names must be unique"
ERROR_OUTPUT_NAMES_UNIQUE: Final = "output path names must be unique"
ERROR_COMMAND_ARGS: Final = "external command requires at least one program argument"
ERROR_TIMEOUT_POSITIVE: Final = "timeout_seconds must be positive"
ERROR_ARTIFACTS_REQUIRE_OUTPUT_ROOT: Final = (
    "artifact patterns require an external command output_root"
)
ERROR_RELATIVE_PATH: Final = "{label} must be a non-empty relative path"
ERROR_COMMAND_NOT_IMPLEMENTED: Final = "{adapter}.command(ctx) must be implemented"

__all__ = [
    "AdapterContext",
    "AdapterValidationError",
    "BaseAdapter",
    "ExternalCommand",
    "ExternalCommandError",
    "ExternalPath",
    "ExternalResult",
    "ExternalWorkspace",
]


@dataclass(frozen=True, slots=True)
class ExternalPath:
    """One path expected by an external tool inside its workspace."""

    path: str
    name: str

    def validate(self) -> None:
        _validate_relative(self.path, ERROR_EXTERNAL_PATH)
        _validate_relative(self.name, ERROR_MANAGED_PATH_NAME)


@dataclass(frozen=True, slots=True)
class ExternalWorkspace:
    """Declarative filesystem contract for an external tool."""

    source_param: str
    default_source: str
    ignored: tuple[str, ...] = DEFAULT_WORKSPACE_IGNORED
    cached: tuple[ExternalPath, ...] = DEFAULT_EXTERNAL_PATHS
    outputs: tuple[ExternalPath, ...] = DEFAULT_EXTERNAL_PATHS

    def validate(self) -> None:
        _require_text(self.source_param, ERROR_SOURCE_PARAM_EMPTY)
        _require_text(self.default_source, ERROR_DEFAULT_SOURCE_EMPTY)

        paths = (*self.cached, *self.outputs)
        for path in paths:
            path.validate()

        _require_unique((path.path for path in paths), ERROR_WORKSPACE_PATHS_UNIQUE)
        _require_unique((path.name for path in self.cached), ERROR_CACHED_NAMES_UNIQUE)
        _require_unique((path.name for path in self.outputs), ERROR_OUTPUT_NAMES_UNIQUE)


@dataclass(frozen=True, slots=True)
class ExternalCommand:
    """Command executed by an external runner."""

    args: tuple[str, ...]
    cwd: Path | None = None
    env: Mapping[str, str] = field(default_factory=dict)
    timeout_seconds: int | None = None
    output_root: Path | None = None
    artifacts: tuple[str, ...] = DEFAULT_ARTIFACTS

    def validate(self) -> None:
        """Validate command shape before it crosses the Rust boundary."""
        if not self.args or not str(self.args[0]).strip():
            raise AdapterValidationError(ERROR_COMMAND_ARGS)

        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise AdapterValidationError(ERROR_TIMEOUT_POSITIVE)

        if self.artifacts and self.output_root is None:
            raise AdapterValidationError(ERROR_ARTIFACTS_REQUIRE_OUTPUT_ROOT)

        for pattern in self.artifacts:
            _validate_relative(pattern, ERROR_ARTIFACT_PATTERN)


@dataclass(frozen=True, slots=True)
class ExternalResult:
    """Result returned by an external command."""

    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


class ExternalCommandError(RuntimeError):
    """Raised when an external command exits unsuccessfully."""

    def __init__(self, name: str, result: ExternalResult) -> None:
        self.name = name
        self.result = result
        super().__init__(f"external command {name!r} {_failure_reason(result)}")


@dataclass(frozen=True, slots=True)
class AdapterContext:
    project_root: Path
    workspace: Path
    outputs: Path
    params: Mapping[str, JsonValue] = field(default_factory=dict)

    def project_path(self, value: str | Path) -> Path:
        return self.project_root / value

    def output_path(self, value: str | Path) -> Path:
        return self.outputs / value


class AdapterValidationError(ValueError):
    """Raised when an adapter declaration is invalid."""


class BaseAdapter:
    """Base class for project-specific external adapters."""

    workspace: ExternalWorkspace | None = None

    def prepare(self, ctx: AdapterContext) -> None:
        """Validate adapter-specific requirements before execution."""

    def command(self, ctx: AdapterContext) -> ExternalCommand:
        raise AdapterValidationError(
            ERROR_COMMAND_NOT_IMPLEMENTED.format(adapter=type(self).__name__)
        )


def _failure_reason(result: ExternalResult) -> str:
    if result.timed_out:
        return "timed out"
    return f"failed with exit code {result.exit_code}"


def _require_text(value: str, message: str) -> None:
    if value.strip():
        return
    raise AdapterValidationError(message)


def _require_unique(values: Iterable[object], message: str) -> None:
    seen: set[object] = set()

    for value in values:
        if value in seen:
            raise AdapterValidationError(message)
        seen.add(value)


def _validate_relative(value: str, label: str) -> None:
    if not value.strip():
        raise AdapterValidationError(ERROR_RELATIVE_PATH.format(label=label))

    path = Path(value)
    if path.is_absolute() or PATH_PARENT in path.parts:
        raise AdapterValidationError(ERROR_RELATIVE_PATH.format(label=label))
