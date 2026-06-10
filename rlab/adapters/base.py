from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, runtime_checkable

from rlab.adapters.context import AdapterContext
from rlab.external.command import ExternalCommand


@runtime_checkable
class ExternalAdapter(Protocol):
    """Lifecycle contract for an external-tool integration.

    Implementations are typically thin classes that wrap a shell command,
    parse its output, and surface the produced files as artifacts. The runner
    calls each hook in the documented order; every hook is optional except
    `command`, which must return the actual `ExternalCommand` to execute.
    """

    name: str

    def prepare(self, ctx: AdapterContext) -> None: ...
    def validate_inputs(self, ctx: AdapterContext) -> tuple[str, ...]: ...
    def command(self, ctx: AdapterContext) -> ExternalCommand: ...
    def collect_outputs(self, ctx: AdapterContext) -> Mapping[str, Path]: ...
    def parse_metrics(self, ctx: AdapterContext) -> Mapping[str, float]: ...
    def register_artifacts(self, ctx: AdapterContext) -> Mapping[str, Path]: ...
    def cleanup(self, ctx: AdapterContext) -> None: ...


class BaseAdapter:
    """Default no-op implementation suitable as a subclass base.

    Provides safe defaults for every optional hook so adapters only override
    what they actually need. Subclasses are required to implement `command`.
    """

    name: str = ""

    def prepare(self, ctx: AdapterContext) -> None:
        for source, target in self.external_output_dirs(ctx).items():
            ctx.external_output_dir(source, target)

    def external_output_dirs(self, ctx: AdapterContext) -> Mapping[str | Path, str | Path]:
        """Map fixed external-tool output directories into artifact storage."""
        return {}

    def validate_inputs(self) -> tuple[str, ...]:
        return ()

    def command(self, ctx: AdapterContext) -> ExternalCommand:
        raise NotImplementedError("ExternalAdapter subclasses must implement .command()")

    def collect_outputs(self) -> Mapping[str, Path]:
        return {}

    def parse_metrics(self) -> Mapping[str, float]:
        return {}

    def register_artifacts(self) -> Mapping[str, Path]:
        return {}

    def cleanup(self) -> None:
        pass
