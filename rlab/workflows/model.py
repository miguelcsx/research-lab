from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    description: str = ""
    fn: Callable[..., Any] | None = None


class ExternalStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    command: tuple[str, ...]
    parser: Callable[..., Any] | str | None = None
    cwd: Path | str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int | None = None
    description: str = ""


class Workflow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    steps: tuple[str | WorkflowStep | ExternalStep, ...]
    description: str = ""
    cache_steps: bool = False
