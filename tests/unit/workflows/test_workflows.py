from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.errors import WorkflowError
from rlab.registry.decorators import register
from rlab.results.bundle import ResultBundle
from rlab.results.metric import Metric
from rlab.runs.layout import RunLayout
from rlab.workflows.context import WorkflowContext
from rlab.workflows.external import _parse_result, run_external_step
from rlab.workflows.model import ExternalStep, Workflow, WorkflowStep
from rlab.workflows.runner import run_workflow


def test_workflow_models_are_immutable() -> None:
    workflow = Workflow(steps=("step.one", "step.two"), description="Test workflow")
    assert len(workflow.steps) == 2
    assert not workflow.cache_steps
    assert WorkflowStep(name="mesh.generate", description="Generate mesh").fn is None
    assert (
        ExternalStep(
            name="lean.build", command=("lake", "build"), timeout_seconds=300
        ).timeout_seconds
        == 300
    )
    with pytest.raises(ValidationError):
        workflow.steps = ("new_step",)


def test_workflow_context_and_runner(runtime: RuntimeContext, tmp_path: Path) -> None:
    run_dir = tmp_path / "run_001"
    RunLayout(root=run_dir).create()
    ctx = runtime.model_copy(update={"run_dir": run_dir, "params": {"nx": 128}})
    wf_ctx = WorkflowContext(runtime=ctx, step_name="solve", step_index=0)
    wf_ctx.log_metric("l2_error", 0.003)
    assert wf_ctx.bundle.metric("solve.l2_error") is not None
    assert wf_ctx.params["nx"] == 128
    assert wf_ctx.seed == 0

    def step_a(_ctx: WorkflowContext) -> ResultBundle:
        return ResultBundle(metrics=(Metric(name="a_metric", value=1.0),))

    def step_dict(_ctx: WorkflowContext) -> dict[str, float]:
        return {"score": 0.95}

    def step_none(ctx: WorkflowContext) -> None:
        ctx.log_metric("progress", 1.0)

    bundle = run_workflow(
        Workflow(
            steps=(
                WorkflowStep(name="step_a", fn=step_a),
                WorkflowStep(name="step_dict", fn=step_dict),
                WorkflowStep(name="step_none", fn=step_none),
            )
        ),
        runtime,
    )
    assert bundle.metric("a_metric") is not None
    assert bundle.metric("score") is not None


def test_workflow_registry_lookup_and_invalid_step(runtime: RuntimeContext) -> None:
    def registered_step(_ctx: WorkflowContext) -> ResultBundle:
        return ResultBundle(metrics=(Metric(name="registry_metric", value=42.0),))

    register(runtime.registry, EntryKind.WORKFLOW, "test.step", registered_step)
    assert (
        run_workflow(Workflow(steps=("test.step",)), runtime).metric("registry_metric") is not None
    )

    with pytest.raises(WorkflowError):
        run_workflow(Workflow(steps=(WorkflowStep(name="no_fn"),)), runtime)


def test_workflow_step_signature_variants(runtime: RuntimeContext) -> None:
    def two_args(_wf_ctx: object, _rt_ctx: object) -> ResultBundle:
        return ResultBundle(metrics=(Metric(name="two_arg_result", value=99.0),))

    def no_args() -> ResultBundle:
        return ResultBundle(metrics=(Metric(name="no_arg_result", value=7.0),))

    assert (
        run_workflow(Workflow(steps=(WorkflowStep(name="two", fn=two_args),)), runtime).metric(
            "two_arg_result"
        )
        is not None
    )
    assert (
        run_workflow(Workflow(steps=(WorkflowStep(name="none", fn=no_args),)), runtime).metric(
            "no_arg_result"
        )
        is not None
    )


def test_external_workflow_step_success_failure_timeout_and_parsers(
    runtime: RuntimeContext, tmp_path: Path
) -> None:
    run_dir = tmp_path / "run_001"
    run_dir.mkdir()
    ctx = runtime.model_copy(update={"run_dir": run_dir})

    success = run_external_step(
        ExternalStep(name="echo_step", command=("echo", "hello_world")), ctx
    )
    assert "runtime_seconds" in success.as_metrics_dict()
    assert "hello_world" in (run_dir / "external" / "echo_step.stdout").read_text(encoding="utf-8")

    parsed = run_external_step(
        ExternalStep(
            name="parsed_step",
            command=("echo", "result"),
            parser=lambda _stdout: {"parsed_score": 1.0},
        ),
        ctx,
    )
    assert parsed.metric("parsed_score") is not None

    with pytest.raises(WorkflowError):
        run_external_step(ExternalStep(name="fail_step", command=("false",)), ctx)
    with pytest.raises(WorkflowError):
        run_external_step(
            ExternalStep(name="slow", command=("sleep", "100"), timeout_seconds=0), ctx
        )


def test_parse_result_variants() -> None:
    bundle = ResultBundle(metrics=(Metric(name="score", value=0.9),))
    assert (
        _parse_result(
            ExternalStep(name="b", command=("echo", "x"), parser=lambda _s: bundle), "out", None
        ).metric("score")
        is not None
    )
    assert (
        _parse_result(
            ExternalStep(name="d", command=("echo", "x"), parser=lambda _s: {"accuracy": 0.8}),
            "out",
            None,
        ).metric("accuracy")
        is not None
    )
    assert _parse_result(ExternalStep(name="n", command=("echo", "x")), "out", None).metrics == ()
