from __future__ import annotations

import inspect
import time
from functools import lru_cache
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
    pass


@lru_cache(maxsize=128)
def _wants_ctx(cls: type, method_name: str) -> bool:
    method = getattr(cls, method_name, None)
    if method is None:
        return False
    params = [p for p in inspect.signature(method).parameters if p != "self"]
    return len(params) > 0


def _call(adapter: object, method_name: str, ctx: AdapterContext) -> Any:
    method = getattr(adapter, method_name)
    if _wants_ctx(type(adapter), method_name):
        return method(ctx)
    return method()


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
    adapter = _resolve_adapter(runtime, adapter_name)
    sandbox = work_dir or _default_work_dir(runtime, adapter_name)
    sandbox.mkdir(parents=True, exist_ok=True)
    ctx = AdapterContext(
        runtime=runtime,
        adapter=adapter_name,
        work_dir=sandbox,
        inputs=dict(inputs or {}),
    )

    _call(adapter, "prepare", ctx)
    violations = _call(adapter, "validate_inputs", ctx)
    if violations:
        raise AdapterValidationError(
            f"Adapter {adapter_name!r} input validation failed: {', '.join(violations)}"
        )

    command = _call(adapter, "command", ctx)
    start = time.perf_counter()
    completed = ShellRunner().run(command, runtime.paths.root)
    elapsed = time.perf_counter() - start

    outputs = dict(_call(adapter, "collect_outputs", ctx))
    metrics = {str(name): float(value) for name, value in _call(adapter, "parse_metrics", ctx).items()}
    artifacts = dict(_call(adapter, "register_artifacts", ctx.with_artifacts(outputs)))
    _call(adapter, "cleanup", ctx)

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
