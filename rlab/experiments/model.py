from collections.abc import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator


class Experiment(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    question: str
    hypothesis: str = ""
    matrix: Mapping[str, Sequence[JsonValue]] = Field(default_factory=dict)
    run: str | None = None
    benchmarks: tuple[str, ...] = ()
    evaluations: tuple[str, ...] = ()
    data: str | None = None
    expected_artifacts: tuple[str, ...] = ()
    seeds: tuple[int, ...] = (0,)

    @field_validator("matrix")
    @classmethod
    def dimensions_are_non_empty(
        cls, value: Mapping[str, Sequence[JsonValue]]
    ) -> Mapping[str, Sequence[JsonValue]]:
        empty = [name for name, choices in value.items() if not choices]
        if empty:
            raise ValueError(f"empty experiment dimensions: {', '.join(empty)}")
        return value
