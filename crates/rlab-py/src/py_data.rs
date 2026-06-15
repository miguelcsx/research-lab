use std::collections::BTreeMap;
use std::fs::File;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple, PyType};
use serde_json::{json, Value};

use crate::convert::json::{from_json_str, to_json, to_pretty_json};
use crate::error::to_py_error;

#[pyclass(name = "ComponentUse", frozen)]
#[derive(Clone)]
pub struct PyComponentUse {
    reference: String,
}

#[pymethods]
impl PyComponentUse {
    #[new]
    pub fn new(reference: String) -> PyResult<Self> {
        rlab_core::ComponentUse::new(reference.clone()).map_err(to_py_error)?;
        Ok(Self { reference })
    }

    #[getter]
    pub fn r#ref(&self) -> String {
        self.reference.clone()
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&rlab_core::ComponentUse::new(self.reference.clone()).map_err(to_py_error)?)
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &serde_json::json!({ "ref": self.reference }))
    }

    pub fn __repr__(&self) -> String {
        format!("ComponentUse({:?})", self.reference)
    }
}

#[pyclass(name = "DataDecision", frozen)]
pub struct PyDataDecision {
    inner: rlab_core::DataDecision,
    record: Option<Py<PyAny>>,
}

#[pymethods]
impl PyDataDecision {
    #[getter]
    pub fn action(&self) -> &'static str {
        match &self.inner {
            rlab_core::DataDecision::Keep { .. } => "keep",
            rlab_core::DataDecision::Update { .. } => "update",
            rlab_core::DataDecision::Drop { .. } => "drop",
            rlab_core::DataDecision::Boundary { .. } => "boundary",
        }
    }

    #[getter]
    pub fn record(&self, py: Python<'_>) -> PyResult<PyObject> {
        if let Some(record) = &self.record {
            return Ok(record.clone_ref(py));
        }
        match &self.inner {
            rlab_core::DataDecision::Keep { record, .. }
            | rlab_core::DataDecision::Update { record, .. } => py_from_json(py, record),
            rlab_core::DataDecision::Boundary { value, .. } => py_from_json(py, value),
            rlab_core::DataDecision::Drop { .. } => Ok(py.None()),
        }
    }

    #[getter]
    pub fn reason(&self) -> Option<String> {
        match &self.inner {
            rlab_core::DataDecision::Update { reason, .. } => reason.clone(),
            rlab_core::DataDecision::Drop { reason, .. } => Some(reason.clone()),
            _ => None,
        }
    }

    #[getter]
    pub fn kind(&self) -> Option<String> {
        match &self.inner {
            rlab_core::DataDecision::Boundary { kind, .. } => Some(kind.clone()),
            _ => None,
        }
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner)
    }

    pub fn __repr__(&self) -> String {
        format!("DataDecision(action={:?})", self.action())
    }
}

#[pyclass(name = "MaterializeReport", frozen)]
pub struct PyMaterializeReport {
    inner: rlab_core::MaterializeReport,
}

#[pymethods]
impl PyMaterializeReport {
    #[getter]
    pub fn written_records(&self) -> usize {
        self.inner.written_records
    }

    #[getter]
    pub fn dropped_records(&self) -> usize {
        self.inner.dropped_records
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&self.inner)
    }
}

#[pyclass(name = "JsonlSource", frozen)]
#[derive(Clone)]
pub struct PyJsonlSource {
    path: PathBuf,
}

#[pymethods]
impl PyJsonlSource {
    #[new]
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    #[getter]
    pub fn path(&self) -> PathBuf {
        self.path.clone()
    }

    #[pyo3(signature = (_ctx=None))]
    pub fn read(&self, py: Python<'_>, _ctx: Option<PyObject>) -> PyResult<PyObject> {
        let file = File::open(&self.path).map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to open JSONL source {}: {error}",
                self.path.display()
            ))
        })?;
        let records = PyList::empty_bound(py);
        for (index, line) in BufReader::new(file).lines().enumerate() {
            let line = line.map_err(|error| {
                pyo3::exceptions::PyOSError::new_err(format!(
                    "failed to read JSONL source {}: {error}",
                    self.path.display()
                ))
            })?;
            let line = line.trim();
            if line.is_empty() {
                continue;
            }
            let value: Value = serde_json::from_str(line).map_err(py_json_error)?;
            if !value.is_object() {
                return Err(PyValueError::new_err(format!(
                    "JSONL record at line {} is not an object",
                    index + 1
                )));
            }
            records.append(py_from_json(py, &value)?)?;
        }
        Ok(records.unbind().into())
    }
}

#[pyclass(name = "JsonlSink", frozen)]
#[derive(Clone)]
pub struct PyJsonlSink {
    path: PathBuf,
}

#[pymethods]
impl PyJsonlSink {
    #[new]
    pub fn new(path: PathBuf) -> Self {
        Self { path }
    }

    #[getter]
    pub fn path(&self) -> PathBuf {
        self.path.clone()
    }

    #[pyo3(signature = (records, _ctx=None))]
    pub fn write(
        &self,
        py: Python<'_>,
        records: PyObject,
        _ctx: Option<PyObject>,
    ) -> PyResult<PyObject> {
        if let Some(parent) = self.path.parent() {
            rlab_core::fs::ensure_dir(parent).map_err(to_py_error)?;
        }
        let mut file = File::create(&self.path).map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to create JSONL sink {}: {error}",
                self.path.display()
            ))
        })?;
        for item in records.bind(py).iter()? {
            let value = py_to_json(py, item?.unbind())?;
            let line = serde_json::to_string(&value).map_err(py_json_error)?;
            writeln!(file, "{line}").map_err(|error| {
                pyo3::exceptions::PyOSError::new_err(format!(
                    "failed to write JSONL sink {}: {error}",
                    self.path.display()
                ))
            })?;
        }
        py_path(py, self.path.clone())
    }
}

#[pyfunction(name = "data_keep")]
pub fn data_keep_py(py: Python<'_>, record: PyObject) -> PyResult<PyDataDecision> {
    let original = record.clone_ref(py);
    Ok(PyDataDecision {
        inner: rlab_core::data_keep(py_to_json(py, record)?),
        record: Some(original),
    })
}

#[pyfunction(name = "data_update")]
#[pyo3(signature = (record, reason=None))]
pub fn data_update_py(
    py: Python<'_>,
    record: PyObject,
    reason: Option<String>,
) -> PyResult<PyDataDecision> {
    let original = record.clone_ref(py);
    Ok(PyDataDecision {
        inner: rlab_core::data_update(py_to_json(py, record)?, reason),
        record: Some(original),
    })
}

#[pyfunction(name = "data_drop")]
pub fn data_drop_py(reason: String) -> PyDataDecision {
    PyDataDecision {
        inner: rlab_core::data_drop(reason),
        record: None,
    }
}

#[pyfunction(name = "data_boundary")]
pub fn data_boundary_py(py: Python<'_>, value: PyObject, kind: String) -> PyResult<PyDataDecision> {
    Ok(PyDataDecision {
        inner: rlab_core::data_boundary(py_to_json(py, value)?, kind),
        record: None,
    })
}

#[pyfunction(name = "materialize_data")]
pub fn materialize_data_py(
    output_dir: PathBuf,
    decisions: Vec<PyRef<'_, PyDataDecision>>,
) -> PyResult<PyMaterializeReport> {
    let decisions = decisions
        .into_iter()
        .map(|decision| decision.inner.clone())
        .collect::<Vec<_>>();
    let inner = rlab_core::materialize_records(&output_dir, decisions).map_err(to_py_error)?;
    Ok(PyMaterializeReport { inner })
}

#[pyfunction(name = "materialize_records")]
pub fn materialize_records_py(
    py: Python<'_>,
    records: PyObject,
    stages: Vec<PyObject>,
) -> PyResult<PyObject> {
    let mut records = iterable_to_vec(py, &records)?;
    let ctx = py.None();
    for stage in stages {
        records = apply_record_stage(py, stage.bind(py), records, ctx.bind(py))?.records;
    }
    Ok(vec_to_py_list(py, &records).unbind().into())
}

#[pyfunction(name = "resolve_data_document")]
#[pyo3(signature = (root, name, overrides_json="{}", require_explicit_paths=true))]
pub fn resolve_data_document_py(
    root: PathBuf,
    name: &str,
    overrides_json: &str,
    require_explicit_paths: bool,
) -> PyResult<String> {
    let overrides: BTreeMap<String, Value> = from_json_str(overrides_json)?;
    let document = rlab_core::resolve_data_document(&root, name, overrides, require_explicit_paths)
        .map_err(to_py_error)?;
    to_json(&document.value)
}

#[pyfunction(name = "list_data_documents")]
pub fn list_data_documents_py(root: PathBuf) -> PyResult<Vec<String>> {
    rlab_core::list_data_documents(&root).map_err(to_py_error)
}

#[pyfunction(name = "validate_data_documents")]
pub fn validate_data_documents_py(root: PathBuf) -> PyResult<String> {
    to_json(&rlab_core::validate_data_documents(&root).map_err(to_py_error)?)
}

#[pyfunction(name = "execute_dataset")]
pub fn execute_dataset_py(
    py: Python<'_>,
    name: String,
    source: PyObject,
    stages: Vec<(String, PyObject, PyObject)>,
    sinks: Vec<PyObject>,
    ctx: PyObject,
) -> PyResult<String> {
    let ctx = ctx.bind(py);
    let mut records = read_source(py, source.bind(py), ctx)?;
    let mut audit = DatasetAudit::default();

    let _ = ctx.call_method1(
        "emit_progress",
        (format!("source read: {} records", records.len()), "info"),
    );

    for (reference, stage, config) in stages {
        let stage = build_stage(py, stage.bind(py), config.bind(py))?;
        let input = records.len();
        let result = apply_stage(py, &stage, records, ctx)?;
        records = result.records;
        audit.dropped += result.dropped;
        merge_counts(&mut audit.reasons, result.reasons);
        audit.stages.push(json!({
            "stage": reference,
            "input": input,
            "output": records.len(),
        }));
        let dropped = result.dropped;
        let output = records.len();
        let _ = ctx.call_method1(
            "emit_progress",
            (
                format!("stage {reference}: {input} → {output} ({dropped} dropped)"),
                "info",
            ),
        );
    }

    let sink_results = write_sinks(py, sinks, &records, ctx)?;
    let _ = ctx.call_method1("emit_progress", ("sinks written", "info"));
    log_dataset_metrics(py, ctx, records.len(), audit.dropped)?;
    write_dataset_audit(py, ctx, &audit, &records)?;

    to_json(&json!({
        "dataset": name,
        "records": records.len(),
        "audit": {
            "dropped": audit.dropped,
            "reasons": audit.reasons,
            "stages": audit.stages,
        },
        "sinks": sink_results,
    }))
}

#[derive(Default)]
struct DatasetAudit {
    dropped: usize,
    reasons: BTreeMap<String, usize>,
    stages: Vec<Value>,
}

struct StageResult {
    records: Vec<PyObject>,
    dropped: usize,
    reasons: BTreeMap<String, usize>,
}

fn read_source(
    py: Python<'_>,
    source: &Bound<'_, PyAny>,
    ctx: &Bound<'_, PyAny>,
) -> PyResult<Vec<PyObject>> {
    let source = materialize(py, source)?;
    if let Some(read) = callable_attr(&source, "read")? {
        return iterable_to_vec(
            py,
            &call_python(py, &read, &[ctx.as_unbound().clone_ref(py)])?,
        );
    }
    if source.is_callable() {
        return iterable_to_vec(
            py,
            &call_python(py, &source, &[ctx.as_unbound().clone_ref(py)])?,
        );
    }
    Err(PyValueError::new_err(
        "dataset source must be callable or expose read(ctx)",
    ))
}

fn build_stage(
    py: Python<'_>,
    stage: &Bound<'_, PyAny>,
    config: &Bound<'_, PyAny>,
) -> PyResult<PyObject> {
    if config
        .downcast::<PyDict>()
        .is_ok_and(|dict| !dict.is_empty())
        && stage.is_callable()
    {
        return Ok(stage.call((), Some(config.downcast::<PyDict>()?))?.unbind());
    }
    Ok(materialize(py, stage)?.unbind())
}

fn apply_stage(
    py: Python<'_>,
    stage: &PyObject,
    records: Vec<PyObject>,
    ctx: &Bound<'_, PyAny>,
) -> PyResult<StageResult> {
    let stage = stage.bind(py);
    if let Some(apply) = callable_attr(stage, "apply")? {
        if !accepts_args(py, &apply, 1)? && !accepts_args(py, &apply, 2)? {
            let args = vec_to_py_list(py, &records);
            let output = call_python(
                py,
                &apply,
                &[args.unbind().into(), ctx.as_unbound().clone_ref(py)],
            )?;
            return Ok(StageResult {
                records: iterable_to_vec(py, &output)?,
                dropped: 0,
                reasons: BTreeMap::new(),
            });
        }
        return apply_record_stage(py, &apply, records, ctx);
    }
    if stage.is_callable() {
        return apply_record_stage(py, stage, records, ctx);
    }
    Err(PyValueError::new_err(
        "dataset stage must be callable or expose apply",
    ))
}

fn apply_record_stage(
    py: Python<'_>,
    callable: &Bound<'_, PyAny>,
    records: Vec<PyObject>,
    ctx: &Bound<'_, PyAny>,
) -> PyResult<StageResult> {
    let mut kept = Vec::with_capacity(records.len());
    let mut reasons = BTreeMap::new();
    let mut dropped = 0;

    for record in records {
        let decision = call_python(
            py,
            callable,
            &[record.clone_ref(py), ctx.as_unbound().clone_ref(py)],
        )?;
        let decision_bound = decision.bind(py);
        match decision_action(decision_bound)? {
            Some(action) if action == "drop" => {
                dropped += 1;
                let reason = decision_bound
                    .getattr("reason")?
                    .extract::<Option<String>>()?
                    .unwrap_or_else(|| "drop".to_string());
                *reasons.entry(reason).or_insert(0) += 1;
            }
            Some(action) if action == "keep" || action == "update" || action == "boundary" => {
                kept.push(decision_bound.getattr("record")?.unbind());
            }
            _ => {
                if decision_bound.is_none() {
                    kept.push(record);
                } else {
                    kept.push(decision);
                }
            }
        }
    }

    Ok(StageResult {
        records: kept,
        dropped,
        reasons,
    })
}

fn write_sinks(
    py: Python<'_>,
    sinks: Vec<PyObject>,
    records: &[PyObject],
    ctx: &Bound<'_, PyAny>,
) -> PyResult<Vec<Value>> {
    let records = vec_to_py_list(py, records);
    sinks
        .into_iter()
        .map(|sink| {
            let sink = materialize(py, sink.bind(py))?;
            let result = if let Some(write) = callable_attr(&sink, "write")? {
                call_python(
                    py,
                    &write,
                    &[
                        records.clone().unbind().into(),
                        ctx.as_unbound().clone_ref(py),
                    ],
                )?
            } else if sink.is_callable() {
                call_python(
                    py,
                    &sink,
                    &[
                        records.clone().unbind().into(),
                        ctx.as_unbound().clone_ref(py),
                    ],
                )?
            } else {
                return Err(PyValueError::new_err(
                    "dataset sink must be callable or expose write(records, ctx)",
                ));
            };
            py_to_json(py, result)
        })
        .collect()
}

fn log_dataset_metrics(
    py: Python<'_>,
    ctx: &Bound<'_, PyAny>,
    records: usize,
    dropped: usize,
) -> PyResult<()> {
    let metrics = PyDict::new_bound(py);
    metrics.set_item("dataset.records", records as f64)?;
    metrics.set_item("dataset.dropped", dropped as f64)?;
    ctx.call_method1("log_metrics", (metrics,))?;
    Ok(())
}

fn write_dataset_audit(
    py: Python<'_>,
    ctx: &Bound<'_, PyAny>,
    audit: &DatasetAudit,
    records: &[PyObject],
) -> PyResult<()> {
    let Some(run_dir) = optional_path(ctx, "run_dir")? else {
        return Ok(());
    };
    let output = run_dir.join("artifacts").join("dataset").join("audit");
    rlab_core::fs::ensure_dir(&output).map_err(to_py_error)?;

    let summary = json!({
        "schema_version": 1,
        "dropped": audit.dropped,
        "reasons": audit.reasons,
        "stages": audit.stages,
        "sources": source_counts(py, records)?,
    });
    let summary_path = output.join("summary.json");
    let drop_reasons_path = output.join("drop_reasons.csv");
    let stage_summary_path = output.join("stage_summary.csv");
    let source_summary_path = output.join("source_summary.csv");

    rlab_core::fs::write_json_atomic(&summary_path, &summary).map_err(to_py_error)?;
    rlab_core::fs::write_text_atomic(&drop_reasons_path, &drop_reasons_csv(&audit.reasons))
        .map_err(to_py_error)?;
    rlab_core::fs::write_text_atomic(&stage_summary_path, &stage_summary_csv(&audit.stages))
        .map_err(to_py_error)?;
    rlab_core::fs::write_text_atomic(&source_summary_path, &source_summary_csv(&summary))
        .map_err(to_py_error)?;

    for path in [
        summary_path,
        drop_reasons_path,
        stage_summary_path,
        source_summary_path,
    ] {
        register_artifact(ctx, path)?;
    }
    Ok(())
}

fn optional_path(ctx: &Bound<'_, PyAny>, name: &str) -> PyResult<Option<PathBuf>> {
    let value = ctx.getattr(name)?;
    if value.is_none() {
        Ok(None)
    } else {
        value.extract()
    }
}

fn register_artifact(ctx: &Bound<'_, PyAny>, path: PathBuf) -> PyResult<()> {
    let name = path
        .file_stem()
        .map(|value| value.to_string_lossy().to_string())
        .unwrap_or_else(|| "dataset_audit".to_string());
    ctx.call_method1("save_artifact", (path, name, "dataset_audit"))?;
    Ok(())
}

fn drop_reasons_csv(reasons: &BTreeMap<String, usize>) -> String {
    let mut csv = "reason,count\n".to_string();
    for (reason, count) in reasons {
        csv.push_str(&format!("{},{}\n", csv_field(reason), count));
    }
    csv
}

fn stage_summary_csv(stages: &[Value]) -> String {
    let mut csv = "stage,input,output\n".to_string();
    for stage in stages {
        csv.push_str(&format!(
            "{},{},{}\n",
            csv_field(
                stage
                    .get("stage")
                    .and_then(Value::as_str)
                    .unwrap_or_default()
            ),
            stage
                .get("input")
                .and_then(Value::as_u64)
                .unwrap_or_default(),
            stage
                .get("output")
                .and_then(Value::as_u64)
                .unwrap_or_default(),
        ));
    }
    csv
}

fn source_summary_csv(summary: &Value) -> String {
    let mut csv = "source,count\n".to_string();
    if let Some(sources) = summary.get("sources").and_then(Value::as_object) {
        for (source, count) in sources {
            csv.push_str(&format!(
                "{},{}\n",
                csv_field(source),
                count.as_u64().unwrap_or_default()
            ));
        }
    }
    csv
}

fn source_counts(py: Python<'_>, records: &[PyObject]) -> PyResult<BTreeMap<String, usize>> {
    let mut counts = BTreeMap::new();
    for record in records {
        if let Some(source) = record_source(py, record)? {
            *counts.entry(source).or_insert(0) += 1;
        }
    }
    Ok(counts)
}

fn record_source(py: Python<'_>, record: &PyObject) -> PyResult<Option<String>> {
    let record = record.bind(py);
    if let Ok(value) = record.get_item("source") {
        if !value.is_none() {
            return Ok(Some(value.str()?.extract()?));
        }
    }
    if record.hasattr("source")? {
        let value = record.getattr("source")?;
        if !value.is_none() {
            return Ok(Some(value.str()?.extract()?));
        }
    }
    Ok(None)
}

fn csv_field(value: &str) -> String {
    if value.contains([',', '"', '\n']) {
        format!("\"{}\"", value.replace('"', "\"\""))
    } else {
        value.to_string()
    }
}

fn decision_action(decision: &Bound<'_, PyAny>) -> PyResult<Option<String>> {
    if !decision.hasattr("action")? {
        return Ok(None);
    }
    decision.getattr("action")?.extract()
}

fn call_python(
    py: Python<'_>,
    callable: &Bound<'_, PyAny>,
    args: &[PyObject],
) -> PyResult<PyObject> {
    if accepts_args(py, callable, args.len())? {
        let tuple = PyTuple::new_bound(py, args.iter().map(|arg| arg.bind(py)));
        return Ok(callable.call1(tuple)?.unbind());
    }
    let tuple = PyTuple::new_bound(
        py,
        args[..args.len().saturating_sub(1)]
            .iter()
            .map(|arg| arg.bind(py)),
    );
    Ok(callable.call1(tuple)?.unbind())
}

fn accepts_args(py: Python<'_>, callable: &Bound<'_, PyAny>, argc: usize) -> PyResult<bool> {
    let inspect = py.import_bound("inspect")?;
    let signature = match inspect.call_method1("signature", (callable,)) {
        Ok(value) => value,
        Err(error)
            if error.is_instance_of::<PyTypeError>(py)
                || error.is_instance_of::<PyValueError>(py) =>
        {
            return Ok(true)
        }
        Err(error) => return Err(error),
    };
    let parameter_type = inspect.getattr("Parameter")?;
    let empty = parameter_type.getattr("empty")?;
    let values = signature.getattr("parameters")?.call_method0("values")?;
    let mut required = 0;
    let mut positional = 0;
    let mut variadic = false;

    for value in values.iter()? {
        let parameter = value?;
        let kind = parameter
            .getattr("kind")?
            .getattr("name")?
            .extract::<String>()?;
        match kind.as_str() {
            "POSITIONAL_ONLY" | "POSITIONAL_OR_KEYWORD" => {
                positional += 1;
                if parameter.getattr("default")?.is(&empty) {
                    required += 1;
                }
            }
            "VAR_POSITIONAL" => variadic = true,
            _ => {}
        }
    }
    Ok(required <= argc && (variadic || argc <= positional))
}

fn materialize<'py>(_py: Python<'py>, value: &Bound<'py, PyAny>) -> PyResult<Bound<'py, PyAny>> {
    if value.is_instance_of::<PyType>() {
        return value.call0();
    }
    Ok(value.clone())
}

fn callable_attr<'py>(
    value: &Bound<'py, PyAny>,
    name: &str,
) -> PyResult<Option<Bound<'py, PyAny>>> {
    if !value.hasattr(name)? {
        return Ok(None);
    }
    let attr = value.getattr(name)?;
    Ok(attr.is_callable().then_some(attr))
}

fn vec_to_py_list<'py>(py: Python<'py>, records: &[PyObject]) -> Bound<'py, PyList> {
    PyList::new_bound(py, records.iter().map(|record| record.bind(py)))
}

fn iterable_to_vec(py: Python<'_>, value: &PyObject) -> PyResult<Vec<PyObject>> {
    let bound = value.bind(py);
    let iterator = bound.iter()?;
    iterator.map(|item| item.map(Bound::unbind)).collect()
}

fn merge_counts(target: &mut BTreeMap<String, usize>, source: BTreeMap<String, usize>) {
    for (key, value) in source {
        *target.entry(key).or_insert(0) += value;
    }
}

fn py_to_json(py: Python<'_>, value: PyObject) -> PyResult<Value> {
    py_any_to_json(py, value.bind(py))
}

fn py_any_to_json(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<Value> {
    if value.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(value) = value.extract::<bool>() {
        return Ok(Value::Bool(value));
    }
    if let Ok(value) = value.extract::<i64>() {
        return Ok(Value::from(value));
    }
    if let Ok(value) = value.extract::<u64>() {
        return Ok(Value::from(value));
    }
    if let Ok(value) = value.extract::<f64>() {
        return serde_json::Number::from_f64(value)
            .map(Value::Number)
            .ok_or_else(|| PyValueError::new_err("JSON value must be finite"));
    }
    if let Ok(value) = value.extract::<String>() {
        return Ok(Value::String(value));
    }
    if let Some(value) = enum_string_value(value)? {
        return Ok(Value::String(value));
    }
    if let Some(value) = method_json_value(py, value, "to_dict")? {
        return Ok(value);
    }
    if let Some(value) = method_json_value(py, value, "model_dump")? {
        return Ok(value);
    }
    if dataclass_instance(py, value)? {
        let asdict = py.import_bound("dataclasses")?.getattr("asdict")?;
        return py_any_to_json(py, &asdict.call1((value,))?);
    }
    if let Ok(dict) = value.downcast::<PyDict>() {
        let mut object = serde_json::Map::new();
        for (key, item) in dict {
            object.insert(key.str()?.extract()?, py_any_to_json(py, &item)?);
        }
        return Ok(Value::Object(object));
    }
    if let Ok(list) = value.downcast::<PyList>() {
        return list
            .iter()
            .map(|item| py_any_to_json(py, &item))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::Array);
    }
    if let Ok(tuple) = value.downcast::<PyTuple>() {
        return tuple
            .iter()
            .map(|item| py_any_to_json(py, &item))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::Array);
    }
    Err(PyTypeError::new_err(format!(
        "value is not JSON-compatible: {}",
        value.get_type().name()?
    )))
}

fn enum_string_value(value: &Bound<'_, PyAny>) -> PyResult<Option<String>> {
    if !value.hasattr("value")? {
        return Ok(None);
    }
    let enum_value = value.getattr("value")?;
    if enum_value.is_callable() {
        return Ok(None);
    }
    enum_value.extract::<String>().map(Some).or(Ok(None))
}

fn method_json_value(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    name: &str,
) -> PyResult<Option<Value>> {
    let Some(method) = callable_attr(value, name)? else {
        return Ok(None);
    };
    py_any_to_json(py, &method.call0()?).map(Some)
}

fn dataclass_instance(py: Python<'_>, value: &Bound<'_, PyAny>) -> PyResult<bool> {
    if value.is_instance_of::<PyType>() {
        return Ok(false);
    }
    py.import_bound("dataclasses")?
        .getattr("is_dataclass")?
        .call1((value,))?
        .extract()
}

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    let raw = to_json(value)?;
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (raw,))?
        .unbind())
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}

fn py_json_error(error: serde_json::Error) -> PyErr {
    PyValueError::new_err(error.to_string())
}
