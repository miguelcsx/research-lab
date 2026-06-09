from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from rlab.constants import EntryKind
from rlab.context.resources import Resources
from rlab.context.runtime import RuntimeContext
from rlab.experiments.model import Experiment, ExperimentMatrix, RetryPolicy
from rlab.registry.context import current_registry
from rlab.registry.decorators import register
from rlab.workflows.model import WorkflowStepResult

ExperimentFn = TypeVar(
    "ExperimentFn",
    bound=Callable[[RuntimeContext], WorkflowStepResult],
)


def experiment(  # noqa: PLR0913
    name: str,
    *,
    question: str,
    hypothesis: str = "",
    decision_criteria: str = "",
    assumptions: tuple[str, ...] = (),
    threats: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    matrix: ExperimentMatrix | None = None,
    workflow: str | None = None,
    benchmarks: tuple[str, ...] = (),
    evaluations: tuple[str, ...] = (),
    data: str | None = None,
    metrics: tuple[str, ...] = (),
    figures: tuple[str, ...] = (),
    tables: tuple[str, ...] = (),
    artifacts: tuple[str, ...] = (),
    required_outputs: tuple[str, ...] = (),
    seeds: tuple[int, ...] = (0,),
    resources: Resources | None = None,
    retry: RetryPolicy | None = None,
    after_run: tuple[str, ...] = (),
    version: str = "1.0.0",
    tags: tuple[str, ...] = (),
) -> Callable[[ExperimentFn], ExperimentFn]:
    """Declare an experiment and its optional Python execution in one place."""

    def decorate(run: ExperimentFn) -> ExperimentFn:
        registry = current_registry()
        register(
            registry,
            EntryKind.WORKFLOW_STEP,
            name,
            run,
            version=version,
            tags=tags,
        )
        register(
            registry,
            EntryKind.EXPERIMENT,
            name,
            Experiment(
                question=question,
                hypothesis=hypothesis,
                decision_criteria=decision_criteria,
                assumptions=assumptions,
                threats=threats,
                references=references,
                matrix=matrix or {},
                run=name,
                workflow=workflow,
                benchmarks=benchmarks,
                evaluations=evaluations,
                data=data,
                metrics=metrics,
                figures=figures,
                tables=tables,
                artifacts=artifacts,
                required_outputs=required_outputs,
                seeds=seeds,
                resources=resources or Resources(),
                retry=retry or RetryPolicy(),
                after_run=after_run,
            ),
            version=version,
            tags=tags,
            declared_by=run,
        )
        return run

    return decorate
