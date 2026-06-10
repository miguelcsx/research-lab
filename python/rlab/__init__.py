"""Python facade for the Rust-backed rlab runtime."""

from pathlib import Path
import json

from ._project import Project
from ._runner import RuntimeContext
from ._decorators import ComponentUse, DataDecision, data_boundary, data_drop, data_keep, data_update
from ._rlab import (
    ArtifactManifest,
    ArtifactStore,
    EffectiveConfig,
    Metric,
    ProductionPolicy,
    Registry,
    RegistryRecord,
    ResultBundle,
    RunDirectory,
    bundle_from_metrics,
    find_project_root,
    load_config,
)
from .baselines import BaselineEntry, BaselineStore
from .benchmarks.model import BenchmarkResult, BenchmarkSpec
from .data import (
    AuditPolicy,
    CheckResult,
    DataAblation,
    DataAction,
    DataBoundary,
    DataCheck,
    DataContext,
    DataExperiment,
    DataMetric,
    DataSink,
    DataSource,
    DatasetSpec,
    PipelineSpec,
    SinkResult,
    classify,
    materialize,
    patterns,
    predicate,
    substitute,
    threshold,
)
from .evaluations.model import EvaluationResult, EvaluationSuite, EvaluationTask, TaskResult
from .experiments.model import (
    Distribution,
    Experiment,
    ExperimentResult,
    Grid,
    RetryPolicy,
    Sample,
    choice,
    factor,
    grid,
    log_uniform,
    uniform,
)
from .results import FigureArtifact, FileArtifact, LogArtifact, ResultSchema, TableArtifact
from .external import (
    AdapterContext,
    AdapterResult,
    AdapterValidationError,
    BaseAdapter,
    ExternalCommand,
    ExternalEvaluation,
    ExternalResult,
)
from .governance import Assumption, LabPolicy, LicenseManifest, Threat, check_compatibility, redact_secrets, scan_for_pii, scan_for_secrets
from .plan import BudgetEstimate, estimate_budget, estimate_required_repetitions
from .stats.compare import MetricComparison, compare_metric_arrays
from .studies.model import Study, StudyPlan
from .units.model import Unit, UnitRegistry
from .workflows.model import ExternalStep, Workflow, WorkflowStep

WorkflowContext = RuntimeContext


# ---------------------------------------------------------------------------
# Module-level decorator shortcuts — delegate to the default Project singleton.
# During runner execution (under pinned_project), Project() returns the pinned
# project, so declarations register into the correct project automatically.
# ---------------------------------------------------------------------------

def experiment(name: str, **metadata):
    """Register an experiment on the default project."""
    return Project().experiment(name, **metadata)


def evaluation(suite: str, task: str, **metadata):
    """Register an evaluation task on the default project."""
    return Project().evaluation(suite, task, **metadata)


def component(kind: str, name: str, **metadata):
    """Register a reusable component on the default project."""
    return Project().component(kind, name, **metadata)


def benchmark(name: str, *, target: str, **metadata):
    """Register a benchmark on the default project."""
    return Project().benchmark(name, target=target, **metadata)


def adapter(name: str, **metadata):
    """Register an adapter on the default project."""
    return Project().adapter(name, **metadata)


def source(name: str, **metadata):
    """Register a dataset source on the default project."""
    return Project().source(name, **metadata)


def transform(name: str, **metadata):
    """Register a record-level transform on the default project."""
    return Project().transform(name, **metadata)


def filter(name: str, **metadata):
    """Register a record-level filter on the default project."""
    return Project().filter(name, **metadata)


def group(name: str, **metadata):
    """Register a batch-level grouping stage on the default project."""
    return Project().group(name, **metadata)


def dedup(name: str, **metadata):
    """Register a batch-level dedup stage on the default project."""
    return Project().dedup(name, **metadata)


def sink(name: str, **metadata):
    """Register a dataset sink on the default project."""
    return Project().sink(name, **metadata)


def check(name: str, **metadata):
    """Register a dataset check on the default project."""
    return Project().check(name, **metadata)


def metric(name: str, **metadata):
    """Register a dataset metric on the default project."""
    return Project().metric(name, **metadata)


def pipeline(name: str, *stages, version: str = "1", tags=(), description: str | None = None):
    """Register a pipeline on the default project."""
    return Project().pipeline(name, *stages, version=version, tags=tags, description=description)


def dataset(name: str, **metadata):
    """Register a dataset declaration on the default project."""
    return Project().dataset(name, **metadata)


def study(name: str, **metadata):
    """Register a study declaration on the default project."""
    return Project().study(name, **metadata)


def workflow(name: str, *, step: str, **metadata):
    """Register a workflow step on the default project."""
    return Project().workflow(name, step=step, **metadata)


def result_schema(name: str, **metadata):
    """Register a result schema on the default project."""
    return Project().result_schema(name, **metadata)


def define_workflow(name: str, *, steps):
    """Create a workflow descriptor outside of a project instance."""
    return Workflow(name=name, steps=tuple(steps))


def compare_runs(path: str | Path = ".rlab/runs", *, metric: str | None = None) -> list[dict[str, object]]:
    """Compare completed run metric summaries from a runs directory.

    This Python helper mirrors the Rust CLI's basic comparison contract for
    notebook and scripting use. Durable CLI output remains Rust-owned.
    """
    root = Path(path)
    rows: list[dict[str, object]] = []
    if not root.exists():
        return rows
    for run_dir in sorted(child for child in root.iterdir() if child.is_dir()):
        summary_path = run_dir / "metrics_summary.json"
        if not summary_path.exists():
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        metrics = summary.get("metrics", summary)
        if not isinstance(metrics, dict):
            continue
        selected = {metric: metrics.get(metric)} if metric else dict(metrics)
        rows.append({"run_id": run_dir.name, "metrics": selected})
    return rows


__all__ = [
    "AdapterContext",
    "AdapterResult",
    "AdapterValidationError",
    "ArtifactManifest",
    "ArtifactStore",
    "Assumption",
    "AuditPolicy",
    "BaseAdapter",
    "BaselineEntry",
    "BaselineStore",
    "BenchmarkResult",
    "BenchmarkSpec",
    "BudgetEstimate",
    "CheckResult",
    "ComponentUse",
    "DataAblation",
    "DataAction",
    "DataBoundary",
    "DataCheck",
    "DataContext",
    "DataDecision",
    "DataExperiment",
    "DataMetric",
    "DataSink",
    "DataSource",
    "DatasetSpec",
    "Distribution",
    "EffectiveConfig",
    "EvaluationResult",
    "EvaluationSuite",
    "EvaluationTask",
    "Experiment",
    "ExperimentResult",
    "ExternalCommand",
    "ExternalEvaluation",
    "ExternalResult",
    "ExternalStep",
    "FileArtifact",
    "FigureArtifact",
    "Grid",
    "LabPolicy",
    "LicenseManifest",
    "LogArtifact",
    "Metric",
    "MetricComparison",
    "PipelineSpec",
    "ProductionPolicy",
    "Project",
    "Registry",
    "RegistryRecord",
    "ResultBundle",
    "ResultSchema",
    "RetryPolicy",
    "RunDirectory",
    "RuntimeContext",
    "Sample",
    "SinkResult",
    "Study",
    "StudyPlan",
    "TableArtifact",
    "TaskResult",
    "Threat",
    "Unit",
    "UnitRegistry",
    "Workflow",
    "WorkflowContext",
    "WorkflowStep",
    "adapter",
    "benchmark",
    "bundle_from_metrics",
    "check",
    "check_compatibility",
    "choice",
    "classify",
    "compare_metric_arrays",
    "compare_runs",
    "component",
    "data_boundary",
    "data_drop",
    "data_keep",
    "data_update",
    "dataset",
    "dedup",
    "define_workflow",
    "estimate_budget",
    "estimate_required_repetitions",
    "evaluation",
    "experiment",
    "factor",
    "filter",
    "find_project_root",
    "grid",
    "group",
    "load_config",
    "log_uniform",
    "materialize",
    "metric",
    "patterns",
    "pipeline",
    "predicate",
    "redact_secrets",
    "result_schema",
    "scan_for_pii",
    "scan_for_secrets",
    "sink",
    "source",
    "study",
    "substitute",
    "threshold",
    "transform",
    "uniform",
    "workflow",
]
