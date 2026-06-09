from __future__ import annotations

import pytest

import rlab
from rlab.evaluations.baseline import ConstantBaseline, MajorityBaseline
from rlab.evaluations.leaderboard import leaderboard
from rlab.evaluations.result import EvaluationResult, TaskResult
from rlab.experiments.model import Experiment
from rlab.power import BudgetEstimate, estimate_budget, estimate_required_repetitions


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
    assert leaderboard("quick", (result,)).models["model:a"]["score.accuracy"] == 1.0


def test_power_and_budget_estimates() -> None:
    small_effect = estimate_required_repetitions(0.01, 1.0)
    large_effect = estimate_required_repetitions(0.5, 1.0)
    assert small_effect > large_effect
    assert estimate_required_repetitions(0.0, 1.0) == 1
    assert estimate_required_repetitions(0.1, 0.0) == 1

    budget = estimate_budget(10, seconds_per_job=3600.0, gpus_per_job=1.0, storage_gb_per_job=5.0)
    assert budget.total_jobs == 10
    assert budget.estimated_gpu_hours == pytest.approx(10.0)
    assert budget.estimated_storage_gb == pytest.approx(50.0)
    assert estimate_budget(
        100, seconds_per_job=3600.0, gpus_per_job=1.0, gpu_hour_cost_usd=2.0
    ).estimated_cost_usd == pytest.approx(200.0)
    assert BudgetEstimate(total_jobs=5, estimated_gpu_hours=10.0).total_jobs == 5


def test_public_api_exports() -> None:
    assert rlab.Experiment is Experiment
    assert callable(rlab.component)
    assert callable(rlab.dataset)
