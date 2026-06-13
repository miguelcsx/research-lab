"""Runner orchestration and target execution."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import cast

from rlab._loader import load_modules
from rlab._project import Project
from rlab._protocol import HostRequest, read_request
from rlab._typing import JsonObject, JsonValue

from .constants import *
from .context import RuntimeContext
from .dataset import execute_dataset, instantiate, resolve_optional, split_ref
from .events import emit_completed, emit_failure, emit_registry_records
from .serde import is_finite_number, jsonable


def main() -> int:
    request_id = "unknown"

    try:
        request = read_request()
        request_id = request.request_id
        os.environ[STRICT_ENV_VAR] = (
            STRICT_ENABLED if request.strict else STRICT_DISABLED
        )

        project = load_modules(
            request.project_root, request.modules, strict=request.strict
        )
        emit_registry_records(request, project.records)

        if request.command == COMMAND_EXECUTE:
            execute(request, project)
        else:
            emit_completed(request, {"ok": True})
    except Exception as exc:
        emit_failure(request_id, exc)

    return 0


def execute(request: HostRequest, project: Project) -> None:
    if request.target is None:
        raise ValueError(ERROR_TARGET_MISSING)

    ctx = RuntimeContext(request)
    ctx.write_manifest(project.records)

    result = execute_target(request, project, ctx)
    ctx.register_outputs()

    if isinstance(result, dict):
        emit_dict_metrics(ctx, result, "")

    ctx.write_manifest(project.records)
    emit_completed(request, result)


def execute_target(
    request: HostRequest, project: Project, ctx: RuntimeContext
) -> object:
    if request.target is None:
        raise ValueError(ERROR_TARGET_MISSING)

    handlers: Mapping[str, Callable[[HostRequest, Project, RuntimeContext], object]] = {
        KIND_DATASET: execute_dataset,
        KIND_STUDY: execute_study,
        KIND_WORKFLOW: execute_workflow,
    }
    handler = handlers.get(request.target.kind)
    if handler is not None:
        return handler(request, project, ctx)

    return invoke_target(
        request,
        project,
        project.resolve(request.target.kind, request.target.name),
        ctx,
    )


def emit_dict_metrics(ctx: RuntimeContext, value: object, prefix: str) -> None:
    flat: dict[str, float] = {}
    flatten_metrics(value, prefix, flat)
    if flat:
        ctx.log_metrics(flat)


def flatten_metrics(node: object, path: str, output: dict[str, float]) -> None:
    if is_finite_number(node):
        if path:
            output[path] = float(node)
        return

    if isinstance(node, Mapping):
        for key, child in node.items():
            flatten_metrics(child, join_metric_path(path, key), output)
        return

    if isinstance(node, list):
        for index, child in enumerate(node):
            flatten_metrics(child, join_metric_path(path, index), output)


def join_metric_path(prefix: str, key: object) -> str:
    return f"{prefix}.{key}" if prefix else str(key)


def execute_workflow(
    request: HostRequest, project: Project, ctx: RuntimeContext
) -> JsonObject:
    if request.target is None:
        raise ValueError(ERROR_WORKFLOW_TARGET)

    workflow_name = request.target.name
    metadata = _mapping(
        project.record(KIND_WORKFLOW, workflow_name).get(KEY_METADATA),
        "workflow metadata",
    )
    steps = metadata.get(KEY_STEPS, [])
    if not isinstance(steps, list) or not steps:
        raise ValueError(ERROR_WORKFLOW_STEPS.format(name=workflow_name))

    return {
        KEY_WORKFLOW: workflow_name,
        KEY_STEPS: [
            execute_workflow_step(project, ctx, workflow_name, step, index)
            for index, step in enumerate(steps)
        ],
    }


def execute_workflow_step(
    project: Project,
    ctx: RuntimeContext,
    workflow_name: str,
    step: object,
    index: int,
) -> JsonObject:
    if not isinstance(step, dict):
        raise ValueError(ERROR_WORKFLOW_STEP_OBJECT)

    name = str(step.get(KEY_NAME, f"step_{index}"))
    ctx.note(f"running workflow step {name}")
    callable_obj = project.resolve(KIND_WORKFLOW_STEP, f"{workflow_name}:{name}")
    result = cast(Callable[[RuntimeContext], object], callable_obj)(ctx)
    return {KEY_NAME: name, KEY_INDEX: index, KEY_RESULT: jsonable(result)}


def execute_study(
    request: HostRequest, project: Project, ctx: RuntimeContext
) -> JsonObject:
    if request.target is None:
        raise ValueError(ERROR_STUDY_TARGET)

    study_name = request.target.name
    experiments = study_experiments(project.record(KIND_STUDY, study_name))
    if not experiments:
        raise ValueError(ERROR_STUDY_EXPERIMENTS.format(name=study_name))

    return {
        KEY_STUDY: study_name,
        KEY_EXPERIMENTS: [
            execute_experiment(project, ctx, name) for name in experiments
        ],
    }


def study_experiments(record: JsonObject) -> list[JsonValue]:
    metadata = record.get(KEY_METADATA, {})
    nested = metadata.get("spec") if isinstance(metadata, dict) else None
    spec = nested if isinstance(nested, dict) else metadata
    experiments = spec.get(KEY_EXPERIMENTS, []) if isinstance(spec, dict) else []
    return experiments if isinstance(experiments, list) else []


def execute_experiment(
    project: Project, ctx: RuntimeContext, experiment_name: object
) -> JsonObject:
    if not isinstance(experiment_name, str) or not experiment_name.strip():
        raise ValueError(ERROR_STUDY_EXPERIMENT_NAME)

    ctx.note(f"running study experiment {experiment_name}")
    callable_obj = project.resolve(KIND_EXPERIMENT, experiment_name)
    result = cast(Callable[[RuntimeContext], object], callable_obj)(ctx)
    return {KEY_EXPERIMENT: experiment_name, KEY_RESULT: jsonable(result)}


def invoke_target(
    request: HostRequest,
    project: Project,
    callable_obj: object,
    ctx: RuntimeContext,
) -> object:
    if request.target is None:
        raise ValueError(ERROR_TARGET_MISSING)

    target_ref = ctx.params.get(KEY_TARGET)
    if isinstance(target_ref, str) and target_ref:
        return cast(Callable[..., object], callable_obj)(
            resolve_component(project, target_ref),
            ctx,
        )

    return cast(Callable[[RuntimeContext], object], callable_obj)(ctx)


def resolve_component(project: Project, reference: object) -> object:
    if not isinstance(reference, str) or REF_SEPARATOR not in reference:
        raise ValueError(ERROR_COMPONENT_REF.format(value=reference))

    head, rest = split_ref(reference)
    if REF_SEPARATOR in rest:
        return resolve_loaded_component(project, rest)

    return materialize_component(project.resolve(head, rest))


def resolve_loaded_component(project: Project, rest: str) -> object:
    loader_name, path = split_ref(rest)
    loader = resolve_optional(project, KIND_LOADER, loader_name)
    if loader is None:
        raise KeyError(ERROR_LOADER_MISSING.format(name=loader_name))

    load = getattr(materialize_component(loader), "load", None)
    if not callable(load):
        raise ValueError(ERROR_LOADER_LOAD.format(name=loader_name))

    return cast(Callable[[str], object], load)(path)


def materialize_component(component: object) -> object:
    if isinstance(component, type):
        return component()

    if callable(component) and not hasattr(component, "__dict__"):
        return component()

    return component


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise TypeError(ERROR_MAPPING.format(label=label))
    return value
