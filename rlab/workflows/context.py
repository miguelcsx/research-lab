from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from rlab.context.runtime import RuntimeContext
from rlab.results.bundle import ResultBundle, empty_bundle
from rlab.results.metric import Metric
from rlab.typing import JsonObject, MetricValue, UnitStr


class WorkflowContext(BaseModel):
    """Step-level context passed to each workflow step function."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    runtime: RuntimeContext
    step_name: str
    step_index: int

    _bundle: ResultBundle = empty_bundle()

    def log_metric(
        self, name: str, value: MetricValue, *, unit: UnitStr = "dimensionless"
    ) -> WorkflowContext:
        m = Metric(name=f"{self.step_name}.{name}", value=value, unit=unit)
        self._bundle = self._bundle.merge(ResultBundle(metrics=(m,)))
        self.runtime.log_metric(name, value, unit=unit)
        return self

    def save_artifact(self, name: str, path: str | Path) -> WorkflowContext:
        self.runtime.save_artifact(f"{self.step_name}/{name}", path)
        return self

    def note(self, text: str) -> WorkflowContext:
        self.runtime.note(f"[{self.step_name}] {text}")
        return self

    @property
    def bundle(self) -> ResultBundle:
        return self._bundle

    # Delegate common context attributes
    @property
    def params(self) -> JsonObject:
        return self.runtime.params

    @property
    def seed(self) -> int:
        return self.runtime.seed
