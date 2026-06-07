from pydantic import BaseModel, ConfigDict, Field

from rlab.context.runtime import RuntimeContext
from rlab.typing import JsonValue


class BenchmarkContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    runtime: RuntimeContext
    benchmark: str
    target: str
    data: str | None = None
    params: dict[str, JsonValue] = Field(default_factory=dict)
