from pydantic import BaseModel, ConfigDict


class BenchmarkSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    target_kind: str
    version: str = "1.0.0"
