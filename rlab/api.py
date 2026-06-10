"""Public surface of rlab.

A clean, typed, side-effect-free set of names. The only entry point for
declarations is :class:`rlab.Project` — every decorator is a bound method on it.
"""
from rlab.adapters import AdapterContext, AdapterResult, AdapterValidationError, BaseAdapter
from rlab.baseline import BaselineEntry, BaselineStore
from rlab.benchmarks import BenchmarkContext, BenchmarkResult, BenchmarkSpec
from rlab.context import RuntimeContext
from rlab.data import (
    Action,
    AuditPolicy,
    CheckResult,
    ComponentMeta,
    ComponentUse,
    DatasetSpec,
    Decision,
    PipelineSpec,
    SinkResult,
    boundary,
    classify,
    drop,
    keep,
    materialize,
    predicate,
    substitute,
    threshold,
    update,
)
from rlab.evaluations import (
    EvaluationResult,
    EvaluationSuite,
    EvaluationTask,
    external_evaluation,
)
from rlab.experiments import Experiment, ExperimentResult
from rlab.experiments.model import RetryPolicy
from rlab.external import ExternalCommand, ExternalEvaluation, ExternalResult
from rlab.manifests import ArtifactManifest, DatasetManifest, ModelManifest, RunManifest
from rlab.power import BudgetEstimate, estimate_budget, estimate_required_repetitions
from rlab.project import Project
from rlab.results import (
    FigureArtifact,
    FileArtifact,
    LogArtifact,
    Metric,
    ResultBundle,
    ResultSchema,
    TableArtifact,
    bundle_from_metrics,
)
from rlab.stats import MetricComparison, compare_metric_arrays, compare_runs
from rlab.studies import Study, StudyPlan
from rlab.workflows import (
    ExternalStep,
    Workflow,
    WorkflowContext,
    WorkflowStep,
    define_workflow,
)

__all__ = [
    "Action",
    "AdapterContext",
    "AdapterResult",
    "AdapterValidationError",
    "ArtifactManifest",
    "AuditPolicy",
    "BaseAdapter",
    "BaselineEntry",
    "BaselineStore",
    "BenchmarkContext",
    "BenchmarkResult",
    "BenchmarkSpec",
    "BudgetEstimate",
    "CheckResult",
    "ComponentMeta",
    "ComponentUse",
    "DatasetManifest",
    "DatasetSpec",
    "Decision",
    "EvaluationResult",
    "EvaluationSuite",
    "EvaluationTask",
    "Experiment",
    "ExperimentResult",
    "ExternalCommand",
    "ExternalEvaluation",
    "ExternalResult",
    "ExternalStep",
    "FigureArtifact",
    "FileArtifact",
    "LogArtifact",
    "Metric",
    "MetricComparison",
    "ModelManifest",
    "PipelineSpec",
    "Project",
    "ResultBundle",
    "ResultSchema",
    "RetryPolicy",
    "RunManifest",
    "RuntimeContext",
    "SinkResult",
    "Study",
    "StudyPlan",
    "TableArtifact",
    "Workflow",
    "WorkflowContext",
    "WorkflowStep",
    "boundary",
    "bundle_from_metrics",
    "classify",
    "compare_metric_arrays",
    "compare_runs",
    "define_workflow",
    "drop",
    "estimate_budget",
    "estimate_required_repetitions",
    "external_evaluation",
    "keep",
    "materialize",
    "predicate",
    "substitute",
    "threshold",
    "update",
]
