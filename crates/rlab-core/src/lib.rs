//! Core domain and durable runtime for rlab.

pub mod artifact;
pub mod baselines;
pub mod benchmarks;
pub mod budget;
pub mod cache;
pub mod ci;
pub mod clean;
pub mod compare;
pub mod config;
pub mod diagnostic;
pub mod error;
pub mod errors;
pub mod evaluations;
pub mod experiments;
pub mod external;
pub mod fs;
pub mod governance;
pub mod graph;
pub mod host;
pub mod jobs;
pub mod journal;
pub mod lint;
pub mod manifest;
pub mod migrate;
pub mod output;
pub mod plan;
pub mod registry;
pub mod reports;
pub mod reproducibility;
pub mod result;
pub mod run;
pub mod search;
pub mod strict;
pub mod table;
pub mod template;
pub mod testing;
pub mod units;

pub mod adapters;
pub mod exec;
pub mod lineage;
pub mod modules;
pub mod stats;
pub mod study;

pub use artifact::{
    describe_artifact_reference, gc_artifacts, parse_artifact_name, parse_artifact_reference,
    prune_runs, resolve_param_refs, resolve_path_reference, ArtifactManifest, ArtifactReference,
    ArtifactStore, PromoteRequest,
};
pub use baselines::{add_baseline, compare_baseline, list_baselines, BaselineComparison};
pub use benchmarks::{BenchmarkContext, BenchmarkResult, BenchmarkSpec};
pub use budget::{estimate_budget, estimate_required_repetitions, BudgetEstimate};
pub use cache::{cache_inspect, cache_list, cache_path, clean_cache, CacheEntry, CacheInspection};
pub use ci::{ci_compare, ci_reproducibility_check, ci_smoke, CiCheckResult};
pub use clean::{clean_project_state, CleanSummary};
pub use compare::{compare_runs, CompareRow};
pub use config::{
    apply_dotted_overrides, diff_documents, list_documents, resolve_document, validate_documents,
    ResolvedDocument,
};
pub use config::{find_project_root, load_effective_config, EffectiveConfig, ProjectPaths};
pub use diagnostic::{doctor_project, DiagnosticFinding, DiagnosticLevel};
pub use error::{RlabError, RlabResult};
pub use errors::{render_run_error, RunErrorReport};
pub use evaluations::{
    BaselineEntry, BaselineStore, EvaluationResult, EvaluationSuite, EvaluationTask,
};
pub use experiments::{
    plan_experiment, plan_record_experiment, ExperimentJob, ExperimentPlan, ExperimentSpec, Grid,
    RetryPolicy,
};
pub use external::{
    run_external_command, safe_environment, ExternalCommand, ExternalResult, ExternalRunnerKind,
};
pub use governance::{
    check_compatibility, redact_secrets, scan_for_pii, scan_for_secrets, LabPolicy,
    LicenseCompatibilitySummary, LicenseManifest, PiiHit, PolicyViolation, SecretHit,
};
pub use graph::{
    add_lineage_edge, add_lineage_edge_at_root, lineage_for, lineage_for_at_root, LineageEdge,
    LineageReport,
};
pub use host::{HostCommand, HostEvent, HostRequest, HostTarget, ProtocolVersion};
pub use jobs::{cancel_job, job_logs, list_jobs, start_job, JobRecord, JobStatus};
pub use journal::{
    add_decision, add_idea, add_negative_result, add_run_note, list_decisions, list_ideas,
    list_negative_results, list_run_notes, promote_idea, search_negative_results, DecisionEntry,
    IdeaEntry, IdeaStatus, NegativeResultEntry, NoteEntry,
};
pub use lint::{lint_project, LintFinding};
pub use plan::{estimate_cost, estimate_power_repetitions, CostPlan, PowerPlan};
pub use registry::{Registry, RegistryKind, RegistryRecord, RegistryRecordSpec};
pub use reports::{
    write_compare_report, write_handoff, write_markdown_card, write_markdown_report,
    write_run_report,
};
pub use result::{FileArtifact, LogArtifact, Metric, MetricDirection, ResultBundle, TableArtifact};
pub use run::{
    all_run_records, query_run_records, RunDirectory, RunId, RunRecord, RunSession, RunStatus,
};
pub use search::{build_search_index, search_project, SearchDocument, SearchHit};
pub use strict::{ProductionPolicy, StrictMode};
pub use table::{render_table, TableRender};
pub use testing::{assert_metric_exists as assert_run_metric_exists, assert_valid_run_dir};
pub use units::{Unit, UnitRegistry};

pub use adapters::{
    adapter_inventory, validate_adapter_descriptor, AdapterCapability, AdapterDescriptor,
    AdapterHealth, AdapterInventory, AdapterStatus,
};
pub use exec::{execute_tracked_command, ExecParser, ExecRequest, ExecRunSummary};
pub use lineage::{impact_report, LineageImpact};
pub use modules::{
    diagnose_modules, list_modules, reload_modules_plan, ModuleDiagnostic, ModuleDiagnosticLevel,
    ModuleReloadPlan, ModuleSummary,
};
pub use stats::{
    compare_metric_arrays, compare_samples, describe_array, paired_bootstrap, DescriptiveStats,
    MetricComparison, SampleComparison,
};
pub use study::{
    plan_registry_study, plan_study, RegistryStudyPlan, Study, StudyExecutionPlan, StudyMode,
    StudyOutcome, StudyPlan,
};
