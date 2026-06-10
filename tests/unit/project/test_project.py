from __future__ import annotations

import rlab
from rlab.constants import EntryKind
from rlab.context.runtime import RuntimeContext
from rlab.experiments.plan import build_plan
from rlab.experiments.runner import execute_experiment


def test_project_registers_into_owned_registry() -> None:
    lab = rlab.Project("team-a")

    @lab.experiment(
        "baseline",
        question="Does the bound decorator register locally?",
        matrix={"value": [1, 2]},
        metrics=("score",),
    )
    def run(ctx: RuntimeContext) -> dict[str, float]:
        return {"score": float(ctx.params["value"])}

    assert "baseline" in {r.name for r in lab.registry.list(EntryKind.EXPERIMENT)}
    # Top-level decorator must not have leaked into a global module.
    import rlab.registry.context as _ctx

    assert _ctx.current_registry().list(EntryKind.EXPERIMENT) == ()


def test_two_projects_do_not_share_state() -> None:
    a = rlab.Project("team-a")
    b = rlab.Project("team-b")

    @a.experiment("shared.name", question="?", matrix={})
    def a_run(_ctx: RuntimeContext) -> dict[str, float]:
        return {}

    @b.experiment("shared.name", question="?", matrix={})
    def b_run(_ctx: RuntimeContext) -> dict[str, float]:
        return {}

    assert a.registry.get(EntryKind.WORKFLOW_STEP, "shared.name").value is a_run
    assert b.registry.get(EntryKind.WORKFLOW_STEP, "shared.name").value is b_run


def test_project_executing_experiment_does_not_read_contextvar() -> None:
    lab = rlab.Project("team")

    @lab.experiment(
        "execute.via.project",
        question="Can we execute through the project?",
        matrix={"value": [1]},
        metrics=("score",),
    )
    def run(ctx: RuntimeContext) -> dict[str, float]:
        return {"score": float(ctx.params["value"])}

    definition = lab.registry.get(EntryKind.EXPERIMENT, "execute.via.project").value
    # Build a runtime whose registry is `lab.registry` so the runner reads from it.
    from rlab.context.factory import build_runtime

    runtime = build_runtime(lab.root or __import__("pathlib").Path.cwd())
    runtime = type(runtime)(  # noqa: PLC001 — rebind registry to the project's
        **{**runtime.__dict__, "registry": lab.registry}
    )
    result = execute_experiment(runtime, build_plan("execute.via.project", definition), definition)
    assert [step.metrics["score"] for step in result.steps] == [1.0]


def test_project_study_and_workflow_decorators_register_locally() -> None:
    lab = rlab.Project("team")

    @lab.study(
        "team.study",
        question="?",
        experiments=("team.exp",),
        outcomes=("score",),
    )
    @lab.experiment("team.exp", question="?", matrix={"value": [1]})
    def exp(_ctx: RuntimeContext) -> dict[str, float]:
        return {"score": 1.0}

    @lab.workflow("team.pipeline", step="prepare")
    def prepare(_ctx: rlab.WorkflowContext) -> dict[str, float]:
        return {"prepared": 1.0}

    assert "team.study" in {r.name for r in lab.registry.list(EntryKind.STUDY)}
    assert "team.exp" in {r.name for r in lab.registry.list(EntryKind.EXPERIMENT)}
    assert "team.pipeline" in {r.name for r in lab.registry.list(EntryKind.WORKFLOW)}
