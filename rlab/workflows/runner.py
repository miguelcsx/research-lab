from __future__ import annotations

import inspect

from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.errors import WorkflowError
from rlab.results.bundle import ResultBundle, bundle_from_metrics, empty_bundle
from rlab.workflows.context import WorkflowContext
from rlab.workflows.external import run_external_step
from rlab.workflows.model import ExternalStep, Workflow, WorkflowStep


def run_workflow(workflow: Workflow, ctx: RuntimeContext) -> ResultBundle:
    """Execute all steps in order, merging their ResultBundles."""
    bundle = empty_bundle()
    for idx, step_ref in enumerate(workflow.steps):
        step_name, step_obj = _resolve_step(step_ref, ctx)
        wf_ctx = WorkflowContext(runtime=ctx, step_name=step_name, step_index=idx)

        if isinstance(step_obj, ExternalStep):
            step_bundle = run_external_step(step_obj, ctx)
        else:
            step_bundle = _run_python_step(step_obj, wf_ctx, ctx)

        bundle = bundle.merge(step_bundle)
    return bundle


def _resolve_step(
    step_ref: str | WorkflowStep | ExternalStep,
    ctx: RuntimeContext,
) -> tuple[str, WorkflowStep | ExternalStep]:
    if isinstance(step_ref, (WorkflowStep, ExternalStep)):
        return step_ref.name, step_ref

    for kind in (EntryKind.WORKFLOW_STEP, EntryKind.WORKFLOW):
        record = ctx.registry.try_get(kind, step_ref)
        if record is None:
            continue
        fn = record.value
        return step_ref, WorkflowStep(name=step_ref, fn=fn)

    raise WorkflowError(
        f"Workflow step {step_ref!r} not found in registry. "
        "Register it with @rlab.workflow_step or pass a WorkflowStep directly."
    )


def _run_python_step(
    step: WorkflowStep,
    wf_ctx: WorkflowContext,
    rt_ctx: RuntimeContext,
) -> ResultBundle:
    if step.fn is None:
        raise WorkflowError(f"Workflow step {step.name!r} has no function")

    sig = inspect.signature(step.fn)
    params = list(sig.parameters.values())

    if not params:
        raw = step.fn()
    elif len(params) == 1:
        raw = step.fn(wf_ctx)
    else:
        raw = step.fn(wf_ctx, rt_ctx)

    if isinstance(raw, ResultBundle):
        return raw
    if isinstance(raw, dict):
        return bundle_from_metrics({k: v for k, v in raw.items() if isinstance(v, (int, float))})
    if raw is None:
        return wf_ctx.bundle
    return empty_bundle()
