from collections.abc import Callable, Mapping
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rlab.results.bundle import ResultBundle
from rlab.typing import MetricValue

WorkflowStepResult = ResultBundle | Mapping[str, MetricValue] | None


WorkflowFn = Callable[..., WorkflowStepResult]
ExternalParser = Callable[[str], WorkflowStepResult]


class WorkflowStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    description: str = ""
    fn: WorkflowFn | None = None


class ExternalStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    command: tuple[str, ...]
    parser: ExternalParser | str | None = None
    cwd: Path | str | None = None
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int | None = None
    description: str = ""


class Workflow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    steps: tuple[str | WorkflowStep | ExternalStep, ...]
    description: str = ""
    cache_steps: bool = False
