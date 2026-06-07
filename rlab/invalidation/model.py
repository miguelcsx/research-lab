from pydantic import BaseModel, ConfigDict


class InvalidationRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    reason: str
    invalidated_at: str
    invalidated_by: str | None = None
    affected: tuple[str, ...] = ()


class ImpactReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject: str
    affected_runs: tuple[str, ...] = ()
    affected_artifacts: tuple[str, ...] = ()
    affected_reports: tuple[str, ...] = ()
    total_affected: int = 0
