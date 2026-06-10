"""rlab — declarative, local-first research runtime.

The public surface lives in :mod:`rlab.api`. Everything reachable from this
package is documented there. The single user-facing entry point for declaring
experiments, studies, workflows, sources, etc. is :class:`rlab.Project`::

    import rlab
    lab = rlab.Project("my-project")

    @lab.experiment("baseline", question="?", matrix={"lr": [1e-3]})
    def run(ctx): ...
"""
from rlab.api import *  # noqa: F401,F403 — public re-export

__all__ = [  # noqa: RUF022 — duplicated from api for tooling that reads it
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
