"""Python facade for the Rust-backed rlab runtime."""

from pathlib import Path
import json

from ._project import Project
from ._loader import discover_modules
from .runner import RuntimeContext
from ._decorators import (
    ComponentUse,
    DataDecision,
    data_boundary,
    data_drop,
    data_keep,
    data_update,
)
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
from .components import ComponentSpec, Requirements, collect_requirements
from .checkpoints import (
    CheckpointManager,
    CheckpointRecord,
    CheckpointSerializer,
    RetentionPolicy,
)
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
from .evaluations.model import (
    EvaluationResult,
    EvaluationSuite,
    EvaluationTask,
    TaskResult,
)
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
from .results import (
    FigureArtifact,
    FileArtifact,
    LogArtifact,
    ResultSchema,
    TableArtifact,
)
from .config import diff_configs, list_configs, resolve_config, validate_configs
from .runs import RunQuery, RunRecord
from ._typing import JsonObject, JsonValue
from .external import (
    AdapterContext,
    AdapterValidationError,
    BaseAdapter,
    ExternalCommand,
    ExternalCommandError,
    ExternalPath,
    ExternalResult,
    ExternalWorkspace,
)
from .governance import (
    Assumption,
    LabPolicy,
    LicenseManifest,
    Threat,
    check_compatibility,
    redact_secrets,
    scan_for_pii,
    scan_for_secrets,
)
from .plan import BudgetEstimate, estimate_budget, estimate_required_repetitions
from .stats.compare import MetricComparison, compare_metric_arrays, paired_bootstrap
from .studies.model import Study, StudyPlan
from .units.model import Unit, UnitRegistry
from .workflows.model import ExternalStep, Workflow, WorkflowStep

WorkflowContext = RuntimeContext


def define_workflow(name: str, *, steps: list[WorkflowStep | ExternalStep]) -> Workflow:
    """Create a workflow descriptor outside of a project instance."""
    return Workflow(name=name, steps=tuple(steps))


def compare_runs(
    path: str | Path = ".rlab/runs", *, metric: str | None = None
) -> list[dict[str, object]]:
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
    "ComponentSpec",
    "CheckpointManager",
    "CheckpointRecord",
    "CheckpointSerializer",
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
    "ExternalCommandError",
    "ExternalPath",
    "ExternalResult",
    "ExternalWorkspace",
    "ExternalStep",
    "FileArtifact",
    "FigureArtifact",
    "Grid",
    "JsonObject",
    "JsonValue",
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
    "Requirements",
    "RetentionPolicy",
    "RetryPolicy",
    "RunDirectory",
    "RunQuery",
    "RunRecord",
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
    "bundle_from_metrics",
    "check_compatibility",
    "choice",
    "classify",
    "compare_metric_arrays",
    "compare_runs",
    "diff_configs",
    "collect_requirements",
    "data_boundary",
    "data_drop",
    "data_keep",
    "data_update",
    "define_workflow",
    "discover_modules",
    "estimate_budget",
    "estimate_required_repetitions",
    "factor",
    "find_project_root",
    "grid",
    "load_config",
    "list_configs",
    "log_uniform",
    "materialize",
    "paired_bootstrap",
    "resolve_config",
    "patterns",
    "predicate",
    "redact_secrets",
    "scan_for_pii",
    "scan_for_secrets",
    "substitute",
    "threshold",
    "uniform",
    "validate_configs",
]
