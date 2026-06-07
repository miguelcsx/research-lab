from pydantic import BaseModel, ConfigDict


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    name: str
    version: str
