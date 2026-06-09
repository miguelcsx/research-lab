from collections.abc import Mapping
from pathlib import Path

from rlab.artifacts.service import promote_path
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.runner import execute_external, execute_suite
from rlab.runs.session import RunSession
from rlab.typing import JsonValue


def _metric_key(suite: str, task: str, name: str) -> str:
    """Prefix metric names with the task ID unless already fully qualified."""
    if name.startswith((f"{suite}.", f"{task}.")):
        return name
    return f"{task}.{name}"


def run_evaluation(  # noqa: PLR0913
    runtime: RuntimeContext,
    suite: str,
    model: str | None = None,
    *,
    baselines: tuple[str, ...] = (),
    split: str | None = None,
    limit: int | None = None,
    batch_size: int | None = None,
    device: str | None = None,
    external_runner: str = "local",
    save_predictions: bool = False,
    upload: bool = False,
    params: Mapping[str, JsonValue] | None = None,
) -> Path:
    model_ref = model or ""
    options = {
        "split": split,
        "limit": limit,
        "batch_size": batch_size,
        "device": device,
        "save_predictions": save_predictions,
        **(params or {}),
    }
    session = RunSession(
        runtime,
        "evaluation",
        suite,
        {
            "suite": suite,
            "model": model_ref,
            "baselines": list(baselines),
            "external_runner": external_runner,
            **options,
        },
    )
    with session.running() as active:
        updated = active.model_copy(
            update={"params": {key: value for key, value in options.items() if value is not None}}
        )
        external_names = {record.name for record in updated.registry.list(EntryKind.EXTERNAL_SUITE)}
        if suite in external_names:
            results = [
                execute_external(updated, suite, reference, external_runner)
                for reference in (model_ref, *baselines)
            ]
        else:
            results = [
                execute_suite(updated, suite, reference) for reference in (model_ref, *baselines)
            ]
        for result in results:
            for task in result.tasks:
                for name, value in task.metrics.items():
                    session.metric(
                        _metric_key(suite, task.task, name),
                        value,
                        suite=suite,
                        model=result.model,
                    )
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
