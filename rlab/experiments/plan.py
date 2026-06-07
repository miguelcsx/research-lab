from pydantic import BaseModel, ConfigDict

from rlab.experiments.matrix import expand_matrix
from rlab.experiments.model import Experiment
from rlab.typing import JsonValue


class ExperimentJob(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    index: int
    seed: int
    params: dict[str, JsonValue]


class ExecutionPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment: str
    jobs: tuple[ExperimentJob, ...]


def build_plan(name: str, experiment: Experiment) -> ExecutionPlan:
    combinations = expand_matrix(experiment.matrix) or ({},)
    pairs = ((seed, params) for seed in experiment.seeds for params in combinations)
    jobs = tuple(
        ExperimentJob(
            id=f"{index:04d}",
            index=index,
            seed=seed,
            params=params,
        )
        for index, (seed, params) in enumerate(pairs)
    )
    return ExecutionPlan(experiment=name, jobs=jobs)
