from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from rlab.experiments.matrix import expand_matrix


class DataAblation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    base: str
    factors: Mapping[str, Sequence[JsonValue]]
    metrics: tuple[str, ...] = ()

    def variants(self) -> tuple[dict[str, JsonValue], ...]:
        return expand_matrix(self.factors)


class DataExperiment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str
    matrix: Mapping[str, Sequence[JsonValue]]
    data_metrics: tuple[str, ...] = ()
    proxy_benchmarks: tuple[str, ...] = ()
    smoke_train: dict[str, JsonValue] = Field(default_factory=dict)
