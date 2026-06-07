import os

from pydantic import BaseModel, ConfigDict


class Resources(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    cpu_count: int = os.cpu_count() or 1
    gpu_count: int = 0
    memory_bytes: int | None = None
    rank: int = 0
    timeout_seconds: int | None = None
    estimated_storage_bytes: int | None = None
