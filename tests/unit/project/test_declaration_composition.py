from __future__ import annotations

import pytest

import rlab
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.evaluations.suite import EvaluationSuite
from rlab.experiments.model import Experiment
from rlab.experiments.plan import build_plan
from rlab.experiments.runner import execute_experiment
from rlab.registry.context import using_registry
from rlab.studies.model import Study
from rlab.workflows.model import Workflow
from rlab.workflows.runner import run_workflow


def test_experiment_decorator_registers_definition_and_run(
    runtime: RuntimeContext,
) -> None:
    with using_registry(runtime.registry):

        @rlab.experiment(
            "test.sweep",
            question="Which value is best?",
            matrix={"value": [1, 2]},
            metrics=("score",),
        )
        def sweep(ctx: RuntimeContext) -> dict[str, float]:
            value = ctx.params["value"]
            assert isinstance(value, int)
            return {"score": float(value)}

    definition = runtime.registry.get(EntryKind.EXPERIMENT, "test.sweep").value
    assert isinstance(definition, Experiment)
    result = execute_experiment(runtime, build_plan("test.sweep", definition), definition)
    assert [step.metrics["score"] for step in result.steps] == [1.0, 2.0]


def test_evaluation_decorators_compose_one_suite(runtime: RuntimeContext) -> None:
    with using_registry(runtime.registry):

        @rlab.evaluation("test.quick", "accuracy", baselines=("model:baseline",))
        def accuracy(_model: object, _ctx: RuntimeContext) -> dict[str, float]:
            return {"accuracy": 1.0}

        @rlab.evaluation("test.quick", "loss")
        def loss(_model: object, _ctx: RuntimeContext) -> dict[str, float]:
            return {"loss": 0.0}

    definition = runtime.registry.get(EntryKind.SUITE, "test.quick").value
    assert isinstance(definition, EvaluationSuite)
    assert tuple(task.name for task in definition.tasks) == ("accuracy", "loss")
    assert definition.baselines == ("model:baseline",)


def test_workflow_decorators_compose_steps_in_order(runtime: RuntimeContext) -> None:
    with using_registry(runtime.registry):

        @rlab.workflow("test.pipeline", step="prepare")
        def prepare(_ctx: rlab.WorkflowContext) -> dict[str, float]:
            return {"prepared": 1.0}

        @rlab.workflow("test.pipeline", step="train")
        def train(_ctx: rlab.WorkflowContext) -> dict[str, float]:
            return {"trained": 1.0}

    definition = runtime.registry.get(EntryKind.WORKFLOW, "test.pipeline").value
    assert isinstance(definition, Workflow)
    assert [step.name for step in definition.steps if isinstance(step, rlab.WorkflowStep)] == [
        "test.pipeline.prepare",
        "test.pipeline.train",
    ]
    assert run_workflow(definition, runtime).as_metrics_dict() == {
        "prepared": 1.0,
        "trained": 1.0,
    }


def test_composed_declarations_reject_duplicate_names(runtime: RuntimeContext) -> None:
    with using_registry(runtime.registry):

        @rlab.evaluation("test.duplicate", "score")
        def first(_model: object, _ctx: RuntimeContext) -> dict[str, float]:
            return {"score": 1.0}

        with pytest.raises(ValueError, match="duplicate evaluation task"):

            @rlab.evaluation("test.duplicate", "score")
            def second(_model: object, _ctx: RuntimeContext) -> dict[str, float]:
                return {"score": 2.0}


def test_study_attaches_to_experiment_declaration(runtime: RuntimeContext) -> None:
    with using_registry(runtime.registry):

        @rlab.study(
            "test.study",
            question="Which value is best?",
            experiments=("test.study.sweep",),
            outcomes=("score",),
        )
        @rlab.experiment(
            "test.study.sweep",
            question="How does value affect score?",
            matrix={"value": [1]},
        )
        def sweep(_ctx: RuntimeContext) -> dict[str, float]:
            return {"score": 1.0}

    definition = runtime.registry.get(EntryKind.STUDY, "test.study").value
    assert isinstance(definition, Study)
    assert definition.experiments == ("test.study.sweep",)


def test_define_workflow_registers_explicit_steps(runtime: RuntimeContext) -> None:
    with using_registry(runtime.registry):
        definition = rlab.define_workflow(
            "test.explicit",
            steps=(
                rlab.WorkflowStep(
                    name="score",
                    fn=lambda: {"score": 1.0},
                ),
            ),
        )

    assert runtime.registry.get(EntryKind.WORKFLOW, "test.explicit").value is definition
    assert run_workflow(definition, runtime).metric("score") is not None
