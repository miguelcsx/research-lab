from __future__ import annotations

import pytest

from rlab.constants import EntryKind, FailureKind
from rlab.context.runtime import RuntimeContext
from rlab.experiments.matrix import Grid, Sample, choice, expand_matrix, factor, log_uniform, uniform
from rlab.experiments.model import Experiment, RetryPolicy
from rlab.experiments.plan import ExecutionPlan, ExperimentJob, build_plan
from rlab.experiments.result import ExperimentResult, ExperimentStep
from rlab.experiments.runner import _classify_error, _classify_exception, execute_experiment
from rlab.experiments.sweep import sweep
from rlab.registry.decorators import register
from rlab.results.bundle import ResultBundle
from rlab.results.metric import Metric


def test_matrix_grid_factor_sample_and_sweep() -> None:
    assert expand_matrix({"a": [1, 2], "b": ["x", "y"]}) == (
        {"a": 1, "b": "x"},
        {"a": 1, "b": "y"},
        {"a": 2, "b": "x"},
        {"a": 2, "b": "y"},
    )
    assert expand_matrix({}) == ({},)
    assert len(Grid({"lr": [0.1, 0.01], "dropout": [0.0, 0.1]}).expand()) == 4
    filtered = Grid({"solver": ["fdtd", "spectral"], "nx": [64, 128, 256]}).where(
        lambda row: not (row["solver"] == "spectral" and row["nx"] == 64)
    )
    assert len(filtered.expand()) == 5
    assert factor("threshold", [0.8, 0.9]).values == (0.8, 0.9)
    assert sweep({"x": [1]}) == ({"x": 1},)


def test_random_samplers_are_bounded_and_reproducible() -> None:
    assert 1e-5 <= log_uniform(1e-5, 1e-3).sample() <= 1e-3
    assert 0.0 <= uniform(0.0, 1.0).sample() <= 1.0
    assert choice(["a", "b", "c"]).sample() in ["a", "b", "c"]
    first = Sample({"x": uniform(0, 1)}, n=5, seed=42).expand()
    second = Sample({"x": uniform(0, 1)}, n=5, seed=42).expand()
    assert first == second


def test_experiment_plan_and_result_models() -> None:
    result = ExperimentResult(
        name="test",
        steps=(ExperimentStep(job_id="0001", params={}, metrics={"acc": 0.9}), ExperimentStep(job_id="0002", params={}, error="OOM")),
    )
    assert len(result.successful_steps) == 1
    assert len(result.failed_steps) == 1
    assert result.is_partial

    plan = ExecutionPlan(
        experiment="ablation",
        jobs=(ExperimentJob(id="0000", index=0, seed=0, params={"lr": 0.001}),),
    )
    assert plan.job_count == 1
    assert plan.dry_run_summary()["experiment"] == "ablation"

    experiment = Experiment(question="q", matrix={"x": [1, 2]}, seeds=(3, 4))
    assert build_plan("test", experiment).job_count == 4
    assert build_plan("empty", Experiment(question="q")).jobs[0].params == {}
    with pytest.raises(ValueError):
        Experiment(question="q", matrix={"x": []})


def test_error_classification() -> None:
    assert _classify_exception(ImportError("no module named x")) == FailureKind.DEPENDENCY_ERROR
    assert _classify_exception(TimeoutError("timed out")) == FailureKind.TIMEOUT
    assert _classify_exception(OverflowError("overflow in computation")) == FailureKind.NUMERICAL_INSTABILITY
    assert _classify_exception(ValueError("invalid input")) == FailureKind.CODE_ERROR
    assert _classify_error("timeout occurred") == FailureKind.TIMEOUT
    assert _classify_error("no module named xyz") == FailureKind.DEPENDENCY_ERROR
    assert _classify_error("nan encountered") == FailureKind.NUMERICAL_INSTABILITY
    assert _classify_error(None) == FailureKind.UNKNOWN


def test_execute_experiment_with_benchmarks_only_skip_and_retry(runtime: RuntimeContext) -> None:
    calls = {"flaky": 0}

    def length_bench(target: object, ctx: object) -> dict[str, float]:
        return {"tokens": float(len(target.encode("test")))}

    def flaky_bench(target: object, ctx: object) -> dict[str, float]:
        calls["flaky"] += 1
        if calls["flaky"] < 2:
            raise RuntimeError("Temporary failure")
        return {"val": 1.0}

    register(runtime.registry, EntryKind.BENCHMARK, "test.length", length_bench, target_kind="tokenizer")
    register(runtime.registry, EntryKind.BENCHMARK, "retry.bench", flaky_bench, target_kind="tokenizer")

    exp = Experiment(question="length test", matrix={"target": ["tokenizer:project.byte"]}, benchmarks=("test.length",))
    assert "test.length.tokens" in execute_experiment(runtime, build_plan("length", exp), exp).steps[0].metrics
    assert execute_experiment(runtime, build_plan("skip", exp), exp, skip=frozenset({"0000"})).steps == ()

    retry_exp = Experiment(
        question="retry test",
        matrix={"target": ["tokenizer:project.byte"]},
        benchmarks=("retry.bench",),
        retry=RetryPolicy(max_attempts=2, delay_seconds=0.0),
    )
    assert execute_experiment(runtime, build_plan("retry", retry_exp), retry_exp, partial=True).steps[0].error is None


def test_execute_experiment_workflow_run_fn_and_evaluations(runtime: RuntimeContext) -> None:
    def workflow_step(_ctx: object) -> ResultBundle:
        return ResultBundle(metrics=(Metric(name="wf_result", value=42.0),))

    def run_fn(_ctx: RuntimeContext) -> dict[str, float]:
        return {"score": 2.72, "cost": 0.5}

    register(runtime.registry, EntryKind.WORKFLOW, "test.workflow", workflow_step)
    register(runtime.registry, EntryKind.WORKFLOW, "run.fn", run_fn)

    workflow_exp = Experiment(question="workflow execution test", matrix={}, workflow="test.workflow")
    assert len(execute_experiment(runtime, build_plan("wf", workflow_exp), workflow_exp).steps) == 1

    run_exp = Experiment(question="run fn test", matrix={}, run="run.fn")
    assert len(execute_experiment(runtime, build_plan("run", run_exp), run_exp).steps) == 1

    eval_exp = Experiment(question="eval test", matrix={"model": ["model:project.constant"]}, evaluations=("project.quick",))
    assert not execute_experiment(runtime, build_plan("eval", eval_exp), eval_exp).failed_steps
