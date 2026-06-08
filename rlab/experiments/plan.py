from pydantic import BaseModel, ConfigDict

from rlab.experiments.matrix import Grid, Sample, expand_matrix
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
    estimated_storage_bytes: int | None = None

    @property
    def job_count(self) -> int:
        return len(self.jobs)

    def dry_run_summary(self) -> dict[str, object]:
        factor_sizes: dict[str, int] = {}
        for job in self.jobs:
            for key, _val in job.params.items():
                if key not in factor_sizes:
                    factor_sizes[key] = 0
                factor_sizes[key] = max(factor_sizes[key], 1)

        # Count unique values per param key
        unique_values: dict[str, set[object]] = {}
        for job in self.jobs:
            for k, v in job.params.items():
                unique_values.setdefault(k, set()).add(str(v))

        return {
            "experiment": self.experiment,
            "total_jobs": self.job_count,
            "matrix": {k: len(v) for k, v in unique_values.items()},
        }


def build_plan(name: str, experiment: Experiment) -> ExecutionPlan:
    matrix = experiment.matrix

    if isinstance(matrix, (Grid, Sample)):
        combinations = matrix.expand() or ({},)
    else:
        combinations = expand_matrix(matrix) or ({},)

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
    return ExecutionPlan(
        experiment=name,
        jobs=jobs,
        estimated_storage_bytes=experiment.resources.estimated_storage_bytes,
    )
