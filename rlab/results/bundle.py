from pydantic import BaseModel, ConfigDict, model_validator

from rlab.results.figure import FigureArtifact
from rlab.results.file import FileArtifact
from rlab.results.log import LogArtifact
from rlab.results.metric import Metric
from rlab.results.table import TableArtifact


class ResultBundle(BaseModel):
    """All outputs produced by a run, benchmark, or workflow step."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    metrics: tuple[Metric, ...] = ()
    tables: tuple[TableArtifact, ...] = ()
    figures: tuple[FigureArtifact, ...] = ()
    files: tuple[FileArtifact, ...] = ()
    logs: tuple[LogArtifact, ...] = ()
    reports: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _unique_names(self) -> "ResultBundle":
        for collection, label in (
            (self.metrics, "metrics"),
            (self.tables, "tables"),
            (self.figures, "figures"),
            (self.files, "files"),
            (self.logs, "logs"),
        ):
            names = [item.name for item in collection]
            duplicates = {n for n in names if names.count(n) > 1}
            if duplicates:
                raise ValueError(f"Duplicate {label} names: {', '.join(sorted(duplicates))}")
        return self

    def merge(self, other: "ResultBundle") -> "ResultBundle":
        """Return a new bundle combining both bundles' outputs."""
        return ResultBundle(
            metrics=self.metrics + other.metrics,
            tables=self.tables + other.tables,
            figures=self.figures + other.figures,
            files=self.files + other.files,
            logs=self.logs + other.logs,
            reports=self.reports + other.reports,
        )

    def metric(self, name: str) -> Metric | None:
        return next((m for m in self.metrics if m.name == name), None)

    def as_metrics_dict(self) -> dict[str, float]:
        return {m.name: float(m.value) for m in self.metrics}


def empty_bundle() -> ResultBundle:
    return ResultBundle()


def bundle_from_metrics(metrics: dict[str, float | int]) -> ResultBundle:

    return ResultBundle(metrics=tuple(Metric(name=k, value=v) for k, v in metrics.items()))
