from pydantic import BaseModel, ConfigDict, Field

from rlab.constants import Direction
from rlab.typing import MetricValue, UnitStr


class Metric(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    value: MetricValue
    unit: UnitStr = "dimensionless"
    direction: Direction = Direction.MINIMIZE
    step: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
