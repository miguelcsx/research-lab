from pathlib import Path

from rlab.context.runtime import RuntimeContext
from rlab.experiments.runner import execute_experiment, plan_experiment
from rlab.runs.reader import RunReader
from rlab.runs.session import RunSession


def run_experiment(  # noqa: PLR0913
    runtime: RuntimeContext,
    path: Path,
    *,
    dry_run: bool = False,
    only: str | None = None,
    tags: tuple[str, ...] = (),
    notes: str | None = None,
    seed: int | None = None,
    run_name: str | None = None,
    resume: Path | None = None,
) -> Path | object:
    plan, experiment = plan_experiment(runtime, path, seed=seed)
    if dry_run:
        return plan
    skip: frozenset[str] = frozenset()
    parent_run = None
    if resume is not None:
        reader = RunReader(resume)
        parent_run = reader.manifest().name
        results = reader.results()
        skip = frozenset(
            step["job_id"] for step in results.get("steps", ()) if step.get("error") is None
        )
    session = RunSession(
        runtime,
        "experiment",
        run_name or plan.experiment,
        {"path": str(path), "only": only},
        tags=tags,
        notes=notes,
        parent_run=parent_run,
    )
    with session.running() as active:
        result = execute_experiment(active, plan, experiment, only=only, skip=skip)
        for step_index, step in enumerate(result.steps):
            for name, value in step.metrics.items():
                session.metric(name, value, step=step_index, job_id=step.job_id)
        session.complete(result)
    return session.layout.root
