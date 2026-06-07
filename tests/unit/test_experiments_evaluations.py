import pytest

import rlab
from rlab.evaluations.baseline import ConstantBaseline, MajorityBaseline
from rlab.evaluations.leaderboard import leaderboard
from rlab.evaluations.result import EvaluationResult, TaskResult
from rlab.experiments.matrix import expand_matrix
from rlab.experiments.model import Experiment
from rlab.experiments.plan import build_plan
from rlab.experiments.sweep import sweep


def test_matrix_plan_and_sweep() -> None:
    experiment = Experiment(
        question="q",
        matrix={"x": [1, 2]},
        seeds=(3, 4),
    )
    assert expand_matrix(experiment.matrix) == ({"x": 1}, {"x": 2})
    plan = build_plan("test", experiment)
    assert len(plan.jobs) == 4
    assert plan.jobs[-1].seed == 4
    assert sweep({"x": [1]}) == ({"x": 1},)
    assert build_plan("empty", Experiment(question="q")).jobs[0].params == {}
    with pytest.raises(ValueError):
        Experiment(question="q", matrix={"x": []})


def test_baselines_and_leaderboard() -> None:
    assert ConstantBaseline(2)(None) == 2
    assert MajorityBaseline(("a", "b", "a"))(None) == "a"
    with pytest.raises(ValueError):
        MajorityBaseline(())
    result = EvaluationResult(
        suite="quick",
        model="model:a",
        tasks=(TaskResult(task="score", metrics={"accuracy": 1.0}),),
    )
    board = leaderboard("quick", (result,))
    assert board.models["model:a"]["score.accuracy"] == 1.0


def test_public_api_exports() -> None:
    assert rlab.Experiment is Experiment
    assert callable(rlab.component)
    assert callable(rlab.data_source)
