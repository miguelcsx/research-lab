from __future__ import annotations

from pathlib import Path
from typing import Any

from rlab.adapters.result import AdapterResult
from rlab.adapters.runner import run_adapter
from rlab.artifacts.service import promote_path
from rlab.context.runtime import RuntimeContext
from rlab.runs.session import RunSession


def execute_adapter(
    runtime: RuntimeContext,
    adapter_name: str,
    *,
    inputs: dict[str, Any] | None = None,
    promote_artifacts: bool = True,
) -> Path:
    """Run an adapter inside a tracked RunSession and return the run directory."""
    params: dict[str, Any] = {"adapter": adapter_name, "inputs": dict(inputs or {})}
    session = RunSession(runtime, "adapter", adapter_name, params)
    active = session.start()
    try:
        work_dir = session.layout.root / "adapters" / adapter_name
        result = run_adapter(active, adapter_name, inputs=inputs, work_dir=work_dir)
        for metric_name, value in result.metrics.items():
            session.metric(metric_name, value, adapter=adapter_name)
        if promote_artifacts:
            _promote_outputs(runtime, adapter_name, result)
        session.complete(result.model_dump(mode="json"))
        return session.layout.root
    except Exception as error:
        session.fail(error)
        raise


def _promote_outputs(runtime: RuntimeContext, adapter_name: str, result: AdapterResult) -> None:
    for name, path in result.artifacts.items():
        if not Path(path).exists():
            continue
        promote_path(
            runtime,
            Path(path),
            artifact_kind="adapter",
            name=f"{adapter_name}.{name}",
            version="1",
            alias="candidate",
        )
