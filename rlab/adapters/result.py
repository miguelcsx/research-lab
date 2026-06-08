from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AdapterResult(BaseModel):
    """Outcome of executing one external-adapter lifecycle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str
    metrics: dict[str, float] = Field(default_factory=dict)
    outputs: dict[str, Path] = Field(default_factory=dict)
    artifacts: dict[str, Path] = Field(default_factory=dict)
    returncode: int = 0
    stdout: str = ""
    stderr: str = ""
    runtime_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.returncode == 0
