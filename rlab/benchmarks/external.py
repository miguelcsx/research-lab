from pydantic import BaseModel, ConfigDict

from rlab.external.model import ExternalEvaluation


class ExternalBenchmark(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    target_kind: str
    evaluation: ExternalEvaluation
