from __future__ import annotations

import signal
import time
from pathlib import Path
from typing import Any

from rlab.benchmarks.runner import execute_benchmark
from rlab.constants import FailureKind, RunStatus
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.runner import execute_external, execute_suite
from rlab.experiments.loader import load_experiment
from rlab.experiments.model import Experiment, RetryPolicy
from rlab.experiments.plan import ExecutionPlan, build_plan
from rlab.experiments.result import ExperimentResult, ExperimentStep
from rlab.manifests.resolver import capture_dataset_manifest
from rlab.results.bundle import ResultBundle, bundle_from_metrics, empty_bundle
from rlab.workflows.runner import run_workflow


def plan_experiment(
    runtime: RuntimeContext,
    path: Path,
    *,
    seed: int | None = None,
) -> tuple[ExecutionPlan, Experiment]:
    name, experiment = load_experiment(runtime.registry, path)
    if seed is not None:
        experiment = experiment.model_copy(update={"seeds": (seed,)})
    return build_plan(name, experiment), experiment


def execute_experiment(
    runtime: RuntimeContext,
    plan: ExecutionPlan,
    experiment: Experiment,
    *,
    only: str | None = None,
    skip: frozenset[str] = frozenset(),
    partial: bool = False,
) -> ExperimentResult:
    if experiment.data and experiment.data.startswith("manifest:"):
        capture_dataset_manifest(runtime, experiment.data)

    steps: list[ExperimentStep] = []
    cancelled = False

    def _handle_sigint(signum: int, frame: Any) -> None:
        nonlocal cancelled
        cancelled = True

    old_handler = signal.signal(signal.SIGINT, _handle_sigint)
    try:
        for job in plan.jobs:
            if cancelled:
                break
            if (only and job.id != only) or job.id in skip:
                continue

            step = _execute_job(runtime, experiment, job.id, job.params, job.seed, retry=experiment.retry)
            steps.append(step)

            if step.error and not partial:
                break
    finally:
        signal.signal(signal.SIGINT, old_handler)

    return ExperimentResult(name=plan.experiment, steps=tuple(steps))


def _execute_job(
    runtime: RuntimeContext,
    experiment: Experiment,
    job_id: str,
    params: dict[str, Any],
    seed: int,
    retry: RetryPolicy,
) -> ExperimentStep:
    last_error: str | None = None
    attempts = max(1, retry.max_attempts)

    for attempt in range(attempts):
        try:
            step = _run_job_once(runtime, experiment, job_id, params, seed)
            if step.error is None:
                return step
            last_error = step.error
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            failure_kind = _classify_exception(exc)
            if retry.on and failure_kind not in retry.on:
                break
            if attempt < attempts - 1 and retry.delay_seconds > 0:
                time.sleep(retry.delay_seconds)

    return ExperimentStep(
        job_id=job_id,
        params=params,
        metrics={},
        error=last_error,
        failure_kind=_classify_error(last_error),
    )


def _run_job_once(
    runtime: RuntimeContext,
    experiment: Experiment,
    job_id: str,
    params: dict[str, Any],
    seed: int,
) -> ExperimentStep:
    ctx = runtime.model_copy(update={"params": {**runtime.params, **params}, "seed": seed})
    metrics: dict[str, float] = {}
    bundle = empty_bundle()

    try:
        # Run workflow if declared
        if experiment.workflow:
            wf_record = ctx.registry.get(__import__("rlab.constants", fromlist=["EntryKind"]).EntryKind.WORKFLOW, experiment.workflow)
            wf = wf_record.value() if callable(wf_record.value) else wf_record.value
            if hasattr(wf, "steps"):
                wf_bundle = run_workflow(wf, ctx)
                bundle = bundle.merge(wf_bundle)
                metrics.update(wf_bundle.as_metrics_dict())

        # Run run function if declared
        if experiment.run:
            EntryKind_ = __import__("rlab.constants", fromlist=["EntryKind"]).EntryKind
            run_record = None
            for kind_ in (EntryKind_.WORKFLOW_STEP, EntryKind_.WORKFLOW):
                try:
                    run_record = ctx.registry.get(kind_, experiment.run)
                    break
                except Exception:
                    continue
            if run_record is None or not callable(run_record.value):
                from rlab.errors import RegistryError
                raise RegistryError(
                    f"Experiment.run={experiment.run!r} must reference a "
                    "@rlab.workflow_step callable"
                )
            fn = run_record.value
            result = fn(ctx)
            if isinstance(result, ResultBundle):
                bundle = bundle.merge(result)
                metrics.update(result.as_metrics_dict())
            elif isinstance(result, dict):
                metrics.update({k: v for k, v in result.items() if isinstance(v, (int, float))})

        # Run benchmarks
        target = params.get("target")
        if isinstance(target, str):
            for bname in experiment.benchmarks:
                bench_result = execute_benchmark(
                    ctx, target, bname, data=experiment.data, params=params
                )
                metrics.update(
                    {f"{bname}.{k}": v for k, v in bench_result.metrics.items()}
                )

        # Run evaluations
        model = params.get("model")
        if isinstance(model, str):
            for sname in experiment.evaluations:
                try:
                    eval_result = execute_suite(ctx, sname, model)
                except Exception:
                    eval_result = execute_external(ctx, sname, model)
                for task in eval_result.tasks:
                    metrics.update(
                        {f"{sname}.{task.task}.{k}": v for k, v in task.metrics.items()}
                    )

    except Exception as exc:  # noqa: BLE001
        return ExperimentStep(
            job_id=job_id,
            params=params,
            metrics=metrics,
            error=str(exc),
            failure_kind=_classify_exception(exc),
        )

    return ExperimentStep(job_id=job_id, params=params, metrics=metrics)


def _classify_exception(exc: Exception) -> FailureKind:
    name = type(exc).__name__.lower()
    if "import" in name or "module" in name:
        return FailureKind.DEPENDENCY_ERROR
    if "timeout" in name:
        return FailureKind.TIMEOUT
    if "overflow" in name or "nan" in name or "inf" in name:
        return FailureKind.NUMERICAL_INSTABILITY
    return FailureKind.CODE_ERROR


def _classify_error(message: str | None) -> FailureKind:
    if not message:
        return FailureKind.UNKNOWN
    msg = message.lower()
    if "timeout" in msg:
        return FailureKind.TIMEOUT
    if "import" in msg or "module" in msg or "no module" in msg:
        return FailureKind.DEPENDENCY_ERROR
    if "nan" in msg or "inf" in msg or "overflow" in msg or "diverge" in msg:
        return FailureKind.NUMERICAL_INSTABILITY
    return FailureKind.CODE_ERROR
