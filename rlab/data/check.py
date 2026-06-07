from pydantic import BaseModel, ConfigDict, Field

from rlab.constants import Severity


class DataCheckResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    success: bool
    severity: Severity = Severity.ERROR
    metrics: dict[str, float] = Field(default_factory=dict)
    message: str = ""
