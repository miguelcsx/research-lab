from __future__ import annotations

import signal
import threading
import time
from pathlib import Path
from typing import Any

from rlab.benchmarks.runner import execute_benchmark
from rlab.constants import EntryKind, FailureKind
from rlab.context.runtime import RuntimeContext
from rlab.errors import RegistryError
from rlab.evaluations.runner import execute_external, execute_suite
from rlab.experiments.loader import load_experiment
from rlab.experiments.model import Experiment
from rlab.experiments.plan import ExecutionPlan, ExperimentJob, build_plan
from rlab.experiments.result import ExperimentResult, ExperimentStep
from rlab.manifests.resolver import capture_dataset_manifest
from rlab.results.bundle import ResultBundle, empty_bundle
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


def execute_experiment(  # noqa: PLR0913
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
    cancelled = threading.Event()

    def _handler(_signum: int, _frame: Any) -> None:
        cancelled.set()

    old_handler = signal.signal(signal.SIGINT, _handler)
    try:
        for job in plan.jobs:
            if cancelled.is_set():
                break
            if (only and job.id != only) or job.id in skip:
                continue

            step = _execute_job(runtime, experiment, job)
            steps.append(step)

            if step.error and not partial:
                break
    finally:
        signal.signal(signal.SIGINT, old_handler)

    return ExperimentResult(name=plan.experiment, steps=tuple(steps))


def _execute_job(
    runtime: RuntimeContext,
    experiment: Experiment,
    job: ExperimentJob,
) -> ExperimentStep:
    retry = experiment.retry
    last_error: str | None = None
    attempts = max(1, retry.max_attempts)

    for attempt in range(attempts):
        try:
            step = _run_job_once(runtime, experiment, job)
            if step.error is None:
                return step
            last_error = step.error
        except Exception as exc:  # noqa: BLE001 — user code may raise anything
            last_error = str(exc)
            failure_kind = _classify_exception(exc)
            if retry.on and failure_kind not in retry.on:
                break
            if attempt < attempts - 1 and retry.delay_seconds > 0:
                time.sleep(retry.delay_seconds)

    return ExperimentStep(
        job_id=job.id,
        params=job.params,
        metrics={},
        error=last_error,
        failure_kind=_classify_error(last_error),
    )


def _run_job_once(
    runtime: RuntimeContext,
    experiment: Experiment,
    job: ExperimentJob,
) -> ExperimentStep:
    ctx = runtime.model_copy(update={"params": {**runtime.params, **job.params}, "seed": job.seed})
    metrics: dict[str, float] = {}
    bundle = empty_bundle()

    try:
        if experiment.workflow:
            bundle, metrics = _run_workflow_step(ctx, experiment, metrics, bundle)
        if experiment.run:
            bundle, metrics = _run_callable_step(ctx, experiment, metrics, bundle)
        metrics = _run_benchmarks(ctx, experiment, job, metrics)
        metrics = _run_evaluations(ctx, experiment, job, metrics)
    except Exception as exc:  # noqa: BLE001 — capture user-code failures into step result
        return ExperimentStep(
            job_id=job.id,
            params=job.params,
            metrics=metrics,
            error=str(exc),
            failure_kind=_classify_exception(exc),
        )

    return ExperimentStep(job_id=job.id, params=job.params, metrics=metrics)


def _run_workflow_step(
    ctx: RuntimeContext,
    experiment: Experiment,
    metrics: dict[str, float],
    bundle: ResultBundle,
) -> tuple[ResultBundle, dict[str, float]]:
    assert experiment.workflow is not None
    wf_record = ctx.registry.get(EntryKind.WORKFLOW, experiment.workflow)
    wf = wf_record.value() if callable(wf_record.value) else wf_record.value
    if hasattr(wf, "steps"):
        wf_bundle = run_workflow(wf, ctx)
        bundle = bundle.merge(wf_bundle)
        metrics = {**metrics, **wf_bundle.as_metrics_dict()}
    return bundle, metrics


def _run_callable_step(
    ctx: RuntimeContext,
    experiment: Experiment,
    metrics: dict[str, float],
    bundle: ResultBundle,
) -> tuple[ResultBundle, dict[str, float]]:
    assert experiment.run is not None
    run_record = None
    for kind_ in (EntryKind.WORKFLOW_STEP, EntryKind.WORKFLOW):
        run_record = ctx.registry.try_get(kind_, experiment.run)
        if run_record is not None:
            break
    if run_record is None or not callable(run_record.value):
        raise RegistryError(
            f"Experiment.run={experiment.run!r} must reference a @rlab.workflow_step callable"
        )
    fn = run_record.value
    result = fn(ctx)
    if isinstance(result, ResultBundle):
        bundle = bundle.merge(result)
        metrics = {**metrics, **result.as_metrics_dict()}
    elif isinstance(result, dict):
        metrics = {
            **metrics,
            **{k: v for k, v in result.items() if isinstance(v, (int, float))},
        }
    return bundle, metrics


def _run_benchmarks(
    ctx: RuntimeContext,
    experiment: Experiment,
    job: ExperimentJob,
    metrics: dict[str, float],
) -> dict[str, float]:
    target = job.params.get("target")
    if not isinstance(target, str):
        return metrics
    for bname in experiment.benchmarks:
        bench_result = execute_benchmark(
            ctx, target, bname, data=experiment.data, params=job.params
        )
        metrics = {
            **metrics,
            **{f"{bname}.{k}": v for k, v in bench_result.metrics.items()},
        }
    return metrics


def _run_evaluations(
    ctx: RuntimeContext,
    experiment: Experiment,
    job: ExperimentJob,
    metrics: dict[str, float],
) -> dict[str, float]:
    model = job.params.get("model")
    if not isinstance(model, str):
        return metrics
    external_suite_names = {r.name for r in ctx.registry.list(EntryKind.EXTERNAL_SUITE)}
    for sname in experiment.evaluations:
        if sname in external_suite_names:
            eval_result = execute_external(ctx, sname, model)
        else:
            eval_result = execute_suite(ctx, sname, model)
        for task in eval_result.tasks:
            metrics = {
                **metrics,
                **{f"{sname}.{task.task}.{k}": v for k, v in task.metrics.items()},
            }
    return metrics


def _classify_exception(exc: Exception) -> FailureKind:
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        return FailureKind.DEPENDENCY_ERROR
    if isinstance(exc, TimeoutError):
        return FailureKind.TIMEOUT
    if isinstance(exc, (FloatingPointError, OverflowError, ArithmeticError)):
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
