from pathlib import Path

from rlab.benchmarks.runner import execute_benchmark
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.runner import execute_external, execute_suite
from rlab.experiments.loader import load_experiment
from rlab.experiments.model import Experiment
from rlab.experiments.plan import ExecutionPlan, build_plan
from rlab.experiments.result import ExperimentResult, ExperimentStep
from rlab.manifests.resolver import capture_dataset_manifest


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
) -> ExperimentResult:
    if experiment.data and experiment.data.startswith("manifest:"):
        capture_dataset_manifest(runtime, experiment.data)
    steps: list[ExperimentStep] = []
    for job in plan.jobs:
        if (only and job.id != only) or job.id in skip:
            continue
        metrics: dict[str, float] = {}
        target = job.params.get("target")
        if isinstance(target, str):
            for benchmark in experiment.benchmarks:
                benchmark_result = execute_benchmark(
                    runtime,
                    target,
                    benchmark,
                    data=experiment.data,
                    params=job.params,
                )
                metrics.update(
                    {
                        f"{benchmark}.{name}": value
                        for name, value in benchmark_result.metrics.items()
                    }
                )
        model = job.params.get("model")
        if isinstance(model, str):
            for suite in experiment.evaluations:
                try:
                    evaluation_result = execute_suite(runtime, suite, model)
                except Exception:
                    evaluation_result = execute_external(runtime, suite, model)
                for task in evaluation_result.tasks:
                    metrics.update(
                        {
                            f"{suite}.{task.task}.{name}": value
                            for name, value in task.metrics.items()
                        }
                    )
        steps.append(ExperimentStep(job_id=job.id, params=job.params, metrics=metrics))
    return ExperimentResult(name=plan.experiment, steps=tuple(steps))
