use pyo3::prelude::*;

use crate::py_artifact::{PyArtifactManifest, PyArtifactStore};
use crate::py_baselines::{PyBaselineEntry, PyBaselineStore};
use crate::py_budget::{estimate_budget_py, estimate_required_repetitions_py, PyBudgetEstimate};
use crate::py_cache::{cache_path_py, cache_size_py, list_cache_py, PyCacheEntry};
use crate::py_checkpoint::{PyCheckpointManager, PyCheckpointRecord, PyRetentionPolicy};
use crate::py_cli::cli_main;
use crate::py_config::{
    apply_overrides_py, diff_config_documents_py, find_project_root_py, list_config_documents_py,
    load_config_py, read_json_manifest_py, resolve_config_document_py,
    validate_config_documents_py, PyEffectiveConfig,
};
use crate::py_data::{
    data_boundary_py, data_drop_py, data_keep_py, data_update_py, execute_dataset_py,
    list_data_documents_py, materialize_data_py, materialize_records_py, resolve_data_document_py,
    validate_data_documents_py, PyComponentUse, PyDataBoundary, PyDataDecision, PyJsonlSink,
    PyJsonlSource, PyMaterializeReport, PyNativeDocumentAssembler, PyNativeSimhashDedup,
    PyNativeTextFilter,
};
use crate::py_external::{
    run_external_command_py, PyExternalCommand, PyExternalPath, PyExternalResult,
    PyExternalWorkspace,
};
use crate::py_governance::{
    check_compatibility_py, redact_secrets_py, scan_for_pii_py, scan_for_secrets_py, PyAssumption,
    PyLabPolicy, PyLicenseCompatibilitySummary, PyLicenseManifest, PyPiiHit, PyPolicyViolation,
    PySecretHit, PyThreat,
};
use crate::py_jobs::PyJobRecord;
use crate::py_journal::{PyDecisionEntry, PyIdeaEntry, PyNegativeResultEntry, PyNoteEntry};
use crate::py_lineage::{add_lineage_edge_py, lineage_for_py};
use crate::py_project::PyProjectCore;
use crate::py_registry::{PyRegistry, PyRegistryRecord};
use crate::py_reports::{write_card_py, write_markdown_report_py};
use crate::py_result::{
    bundle_from_metrics, PyFigureArtifact, PyFileArtifact, PyLogArtifact, PyMetric, PyResultBundle,
    PyResultSchema, PyTableArtifact,
};
use crate::py_run::{
    failed_host_event_line, PyRunDirectory, PyRunHandle, PyRunQuery, PyRunRecord, PyRuntimeContext,
};
use crate::py_stats::{compare_metric_arrays_py, paired_bootstrap_py, PyMetricComparison};
use crate::py_strict::PyProductionPolicy;
use crate::py_testing::{assert_metric_exists_py, assert_valid_run_dir_py};
use crate::py_units::{PyUnit, PyUnitRegistry};

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    register_functions(module)?;
    register_classes(module)
}

fn register_functions(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(cli_main, module)?)?;
    module.add_function(wrap_pyfunction!(find_project_root_py, module)?)?;
    module.add_function(wrap_pyfunction!(load_config_py, module)?)?;
    module.add_function(wrap_pyfunction!(resolve_config_document_py, module)?)?;
    module.add_function(wrap_pyfunction!(list_config_documents_py, module)?)?;
    module.add_function(wrap_pyfunction!(validate_config_documents_py, module)?)?;
    module.add_function(wrap_pyfunction!(diff_config_documents_py, module)?)?;
    module.add_function(wrap_pyfunction!(apply_overrides_py, module)?)?;
    module.add_function(wrap_pyfunction!(read_json_manifest_py, module)?)?;
    module.add_function(wrap_pyfunction!(bundle_from_metrics, module)?)?;
    module.add_function(wrap_pyfunction!(run_external_command_py, module)?)?;
    module.add_function(wrap_pyfunction!(data_keep_py, module)?)?;
    module.add_function(wrap_pyfunction!(data_update_py, module)?)?;
    module.add_function(wrap_pyfunction!(data_drop_py, module)?)?;
    module.add_function(wrap_pyfunction!(data_boundary_py, module)?)?;
    module.add_function(wrap_pyfunction!(materialize_data_py, module)?)?;
    module.add_function(wrap_pyfunction!(materialize_records_py, module)?)?;
    module.add_function(wrap_pyfunction!(execute_dataset_py, module)?)?;
    module.add_function(wrap_pyfunction!(resolve_data_document_py, module)?)?;
    module.add_function(wrap_pyfunction!(list_data_documents_py, module)?)?;
    module.add_function(wrap_pyfunction!(validate_data_documents_py, module)?)?;
    module.add_function(wrap_pyfunction!(add_lineage_edge_py, module)?)?;
    module.add_function(wrap_pyfunction!(lineage_for_py, module)?)?;
    module.add_function(wrap_pyfunction!(compare_metric_arrays_py, module)?)?;
    module.add_function(wrap_pyfunction!(paired_bootstrap_py, module)?)?;
    module.add_function(wrap_pyfunction!(write_markdown_report_py, module)?)?;
    module.add_function(wrap_pyfunction!(write_card_py, module)?)?;
    module.add_function(wrap_pyfunction!(cache_path_py, module)?)?;
    module.add_function(wrap_pyfunction!(list_cache_py, module)?)?;
    module.add_function(wrap_pyfunction!(cache_size_py, module)?)?;
    module.add_function(wrap_pyfunction!(estimate_budget_py, module)?)?;
    module.add_function(wrap_pyfunction!(estimate_required_repetitions_py, module)?)?;
    module.add_function(wrap_pyfunction!(redact_secrets_py, module)?)?;
    module.add_function(wrap_pyfunction!(scan_for_secrets_py, module)?)?;
    module.add_function(wrap_pyfunction!(scan_for_pii_py, module)?)?;
    module.add_function(wrap_pyfunction!(check_compatibility_py, module)?)?;
    module.add_function(wrap_pyfunction!(assert_valid_run_dir_py, module)?)?;
    module.add_function(wrap_pyfunction!(assert_metric_exists_py, module)?)?;
    module.add_function(wrap_pyfunction!(failed_host_event_line, module)?)?;

    Ok(())
}

fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyEffectiveConfig>()?;
    module.add_class::<PyProjectCore>()?;
    module.add_class::<PyRegistry>()?;
    module.add_class::<PyRegistryRecord>()?;
    module.add_class::<PyMetric>()?;
    module.add_class::<PyResultBundle>()?;
    module.add_class::<PyFileArtifact>()?;
    module.add_class::<PyFigureArtifact>()?;
    module.add_class::<PyTableArtifact>()?;
    module.add_class::<PyLogArtifact>()?;
    module.add_class::<PyResultSchema>()?;
    module.add_class::<PyRuntimeContext>()?;
    module.add_class::<PyRunDirectory>()?;
    module.add_class::<PyRunHandle>()?;
    module.add_class::<PyRunRecord>()?;
    module.add_class::<PyRunQuery>()?;
    module.add_class::<PyComponentUse>()?;
    module.add_class::<PyDataDecision>()?;
    module.add_class::<PyDataBoundary>()?;
    module.add_class::<PyNativeTextFilter>()?;
    module.add_class::<PyNativeSimhashDedup>()?;
    module.add_class::<PyNativeDocumentAssembler>()?;
    module.add_class::<PyMaterializeReport>()?;
    module.add_class::<PyJsonlSource>()?;
    module.add_class::<PyJsonlSink>()?;
    module.add_class::<PyArtifactManifest>()?;
    module.add_class::<PyArtifactStore>()?;
    module.add_class::<PyBaselineEntry>()?;
    module.add_class::<PyBaselineStore>()?;
    module.add_class::<PyCacheEntry>()?;
    module.add_class::<PyBudgetEstimate>()?;
    module.add_class::<PyExternalPath>()?;
    module.add_class::<PyExternalWorkspace>()?;
    module.add_class::<PyExternalCommand>()?;
    module.add_class::<PyExternalResult>()?;
    module.add_class::<PyCheckpointManager>()?;
    module.add_class::<PyCheckpointRecord>()?;
    module.add_class::<PyRetentionPolicy>()?;
    module.add_class::<PyMetricComparison>()?;
    module.add_class::<PyProductionPolicy>()?;
    module.add_class::<PyAssumption>()?;
    module.add_class::<PyThreat>()?;
    module.add_class::<PySecretHit>()?;
    module.add_class::<PyPiiHit>()?;
    module.add_class::<PyLicenseManifest>()?;
    module.add_class::<PyLicenseCompatibilitySummary>()?;
    module.add_class::<PyPolicyViolation>()?;
    module.add_class::<PyLabPolicy>()?;
    module.add_class::<PyJobRecord>()?;
    module.add_class::<PyDecisionEntry>()?;
    module.add_class::<PyIdeaEntry>()?;
    module.add_class::<PyNegativeResultEntry>()?;
    module.add_class::<PyNoteEntry>()?;
    module.add_class::<PyUnit>()?;
    module.add_class::<PyUnitRegistry>()?;

    Ok(())
}
