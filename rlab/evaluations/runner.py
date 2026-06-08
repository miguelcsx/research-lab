import inspect
import shutil
from typing import Any, cast

import yaml

from rlab.components.builders import try_build_component
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.result import EvaluationResult, TaskResult
from rlab.evaluations.suite import EvaluationSuite
from rlab.external.model import ExternalEvaluation
from rlab.external.parser import json_metrics
from rlab.external.runner import DockerRunner, ExternalRunner, ShellRunner


def _definition(value: Any, expected: type[Any]) -> Any:
    result = value() if callable(value) and not inspect.isclass(value) else value
    if not isinstance(result, expected):
        raise TypeError(f"Expected {expected.__name__}, got {type(result).__name__}")
    return result


def execute_suite(
    runtime: RuntimeContext,
    suite_name: str,
    model_ref: str,
) -> EvaluationResult:
    record = runtime.registry.get(EntryKind.SUITE, suite_name)
    suite = cast(EvaluationSuite, _definition(record.value, EvaluationSuite))
    built = try_build_component(runtime.registry, model_ref)
    model = built if built is not None else model_ref
    tasks = tuple(
        TaskResult(
            task=task.name,
            metrics={name: float(value) for name, value in task.evaluator(model, runtime).items()},
        )
        for task in suite.tasks
    )
    return EvaluationResult(suite=suite_name, model=model_ref, tasks=tasks)


def execute_external(
    runtime: RuntimeContext,
    suite_name: str,
    model_ref: str,
    runner_name: str = "local",
) -> EvaluationResult:
    record = runtime.registry.get(EntryKind.EXTERNAL_SUITE, suite_name)
    definition = cast(ExternalEvaluation, _definition(record.value, ExternalEvaluation))
    command = definition.command.model_copy(
        update={
            "args": tuple(part.format(model=model_ref) for part in definition.command.args),
        }
    )
    runner: ExternalRunner = ShellRunner()
    if runner_name == "docker":
        image = runtime.config.launcher.docker_image
        if image is None:
            raise ValueError("launcher.docker_image is required for Docker evaluations")
        command = DockerRunner().command(
            image,
            *command.args,
            mounts=((runtime.paths.root, "/workspace"),),
            cwd=command.cwd,
            env=command.env,
            timeout_seconds=command.timeout_seconds,
        )
        runner = DockerRunner()
    elif runner_name not in {"local", "subprocess"}:
        raise ValueError(f"Unsupported external runner {runner_name!r}")
    result = runner.run(command, runtime.paths.root)
    if runtime.run_dir is None:
        raise RuntimeError("External evaluation requires an active run")
    external = runtime.run_dir / "external" / suite_name
    external.mkdir(parents=True, exist_ok=True)
    (external / "external_eval.yaml").write_text(
        yaml.safe_dump(definition.model_dump(mode="json"), sort_keys=False)
    )
    (external / "stdout.log").write_text(result.stdout)
    (external / "stderr.log").write_text(result.stderr)
    output = definition.output
    if not output.is_absolute():
        output = (command.cwd or runtime.paths.root) / output
    preserved = external / "raw" / output.name
    preserved.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output, preserved)
    parsers = {"json": json_metrics}
    metrics = parsers[definition.parser](output)
    return EvaluationResult(
        suite=suite_name,
        model=model_ref,
        tasks=(TaskResult(task=suite_name, metrics=metrics),),
    )
