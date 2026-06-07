from pydantic import BaseModel, ConfigDict

from rlab.evaluations.task import EvaluationTask


class EvaluationSuite(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    tasks: tuple[EvaluationTask, ...]
    baselines: tuple[str, ...] = ()
