from __future__ import annotations

import subprocess
import time
from pathlib import Path

from rlab.context.runtime import RuntimeContext
from rlab.errors import WorkflowError
from rlab.results.bundle import ResultBundle, bundle_from_metrics
from rlab.workflows.model import ExternalStep


def run_external_step(step: ExternalStep, ctx: RuntimeContext) -> ResultBundle:
    cwd = Path(str(step.cwd)) if step.cwd else None
    env: dict[str, str] | None = step.env or None

    start = time.monotonic()
    try:
        result = subprocess.run(
            list(step.command),
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkflowError(
            f"External step {step.name!r} timed out after {step.timeout_seconds}s"
        ) from exc
    elapsed = time.monotonic() - start

    if ctx.run_dir:
        log_file = ctx.run_dir / "external" / f"{step.name}.stdout"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.write_text(result.stdout)
        err_file = ctx.run_dir / "external" / f"{step.name}.stderr"
        err_file.write_text(result.stderr)

    if result.returncode != 0:
        raise WorkflowError(
            f"External step {step.name!r} failed (exit {result.returncode}):\n{result.stderr[-2000:]}"
        )

    parsed = _parse_result(step, result.stdout, ctx.run_dir)
    return parsed.merge(bundle_from_metrics({"runtime_seconds": elapsed}))


def _parse_result(
    step: ExternalStep,
    stdout: str,
    run_dir: Path | None,
) -> ResultBundle:
    if step.parser is None:
        return ResultBundle()

    if callable(step.parser):
        raw = step.parser(stdout)
    elif isinstance(step.parser, str) and ":" in step.parser:
        import importlib
        module_path, func_name = step.parser.rsplit(":", 1)
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
        raw = func(stdout)
    else:
        return ResultBundle()

    if isinstance(raw, ResultBundle):
        return raw
    if isinstance(raw, dict):
        return bundle_from_metrics(raw)
    return ResultBundle()
