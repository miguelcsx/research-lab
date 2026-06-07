from pathlib import Path

from rlab.artifacts.service import promote_path
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.runner import execute_external, execute_suite
from rlab.runs.session import RunSession


def run_evaluation(  # noqa: PLR0913
    runtime: RuntimeContext,
    suite: str,
    model: str,
    *,
    baselines: tuple[str, ...] = (),
    split: str | None = None,
    limit: int | None = None,
    batch_size: int | None = None,
    device: str | None = None,
    external_runner: str = "local",
    save_predictions: bool = False,
    upload: bool = False,
) -> Path:
    options = {
        "split": split,
        "limit": limit,
        "batch_size": batch_size,
        "device": device,
        "save_predictions": save_predictions,
    }
    session = RunSession(
        runtime,
        "evaluation",
        suite,
        {
            "suite": suite,
            "model": model,
            "baselines": list(baselines),
            "external_runner": external_runner,
            **options,
        },
    )
    active = session.start().model_copy(
        update={"params": {key: value for key, value in options.items() if value is not None}}
    )
    try:
        external_names = {record.name for record in active.registry.list(EntryKind.EXTERNAL_SUITE)}
        if suite in external_names:
            results = [
                execute_external(active, suite, reference, external_runner)
                for reference in (model, *baselines)
            ]
        else:
            results = [execute_suite(active, suite, reference) for reference in (model, *baselines)]
        for result in results:
            for task in result.tasks:
                for name, value in task.metrics.items():
                    session.metric(f"{task.task}.{name}", value, suite=suite, model=result.model)
        session.complete(
            {"suite": suite, "results": [result.model_dump(mode="json") for result in results]}
        )
        if upload:
            promote_path(
                runtime,
                session.layout.results,
                artifact_kind="evaluation",
                name=suite,
                version=session.manifest.name,
                alias="candidate",
            )
        return session.layout.root
    except Exception as error:
        session.fail(error)
        raise
