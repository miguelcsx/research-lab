from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from rlab.adapters.base import BaseAdapter, ExternalAdapter
from rlab.adapters.context import AdapterContext
from rlab.adapters.result import AdapterResult
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.errors import RegistryError, RlabError
from rlab.external.runner import ShellRunner


class AdapterValidationError(RlabError):
    """Raised when an adapter rejects its inputs."""


def _resolve_adapter(runtime: RuntimeContext, adapter_name: str) -> ExternalAdapter:
    record = runtime.registry.get(EntryKind.ADAPTER, adapter_name)
    factory = record.value
    instance = factory() if callable(factory) and not _is_adapter_instance(factory) else factory
    if not isinstance(instance, BaseAdapter) and not isinstance(instance, ExternalAdapter):
        raise RegistryError(
            f"Adapter {adapter_name!r} must inherit BaseAdapter or implement ExternalAdapter"
        )
    if not getattr(instance, "name", "") and isinstance(instance, BaseAdapter):
        instance.name = adapter_name
    return instance


def _is_adapter_instance(value: Any) -> bool:
    return isinstance(value, BaseAdapter) or (
        isinstance(value, ExternalAdapter) and not isinstance(value, type)
    )


def run_adapter(
    runtime: RuntimeContext,
    adapter_name: str,
    *,
    inputs: dict[str, Any] | None = None,
    work_dir: Path | None = None,
) -> AdapterResult:
    """Execute an adapter end-to-end and return its result.

    The lifecycle: prepare → validate_inputs → command → execute →
    collect_outputs → parse_metrics → register_artifacts → cleanup.
    Any validation error is raised as `AdapterValidationError`; command failures
    propagate as `ExternalRunError` from the runner.
    """
    adapter = _resolve_adapter(runtime, adapter_name)
    sandbox = work_dir or _default_work_dir(runtime, adapter_name)
    sandbox.mkdir(parents=True, exist_ok=True)
    ctx = AdapterContext(
        runtime=runtime,
        adapter=adapter_name,
        work_dir=sandbox,
        inputs=dict(inputs or {}),
    )

    adapter.prepare(ctx)
    violations = adapter.validate_inputs(ctx)
    if violations:
        raise AdapterValidationError(
            f"Adapter {adapter_name!r} input validation failed: {', '.join(violations)}"
        )

    command = adapter.command(ctx)
    start = time.perf_counter()
    completed = ShellRunner().run(command, runtime.paths.root)
    elapsed = time.perf_counter() - start

    outputs = dict(adapter.collect_outputs(ctx))
    metrics = {str(name): float(value) for name, value in adapter.parse_metrics(ctx).items()}
    artifacts = dict(adapter.register_artifacts(ctx.with_artifacts(outputs)))
    adapter.cleanup(ctx)

    return AdapterResult(
        adapter=adapter_name,
        metrics=metrics,
        outputs=outputs,
        artifacts=artifacts,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        runtime_seconds=elapsed,
    )


def _default_work_dir(runtime: RuntimeContext, adapter_name: str) -> Path:
    base = runtime.run_dir or runtime.paths.cache
    return base / "adapters" / adapter_name
