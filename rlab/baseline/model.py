from pydantic import BaseModel, ConfigDict


class BaselineEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: str = "run"
    run_id: str | None = None
    metric: str = ""
    value: float | None = None
    description: str = ""
    for_project: str = ""
    source: str = ""
    tags: tuple[str, ...] = ()
