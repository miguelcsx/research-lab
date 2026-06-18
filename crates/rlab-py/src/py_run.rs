use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde_json::{json, Value};

use rlab_core::host::{HostEvent, LogEvent, ProgressEvent, ProtocolVersion};

use crate::convert::json::{from_json_str, to_json};
use crate::error::to_py_error;
use crate::py_external::{PyExternalCommand, PyExternalResult, PyExternalWorkspace};

const CHILD_RUNS_FILE: &str = "child_runs.jsonl";
const ENV_PARENT_RUN_ID: &str = "RLAB_PARENT_RUN_ID";
const ENV_PARENT_TARGET: &str = "RLAB_PARENT_TARGET";
const ENV_NESTED_DEPTH: &str = "RLAB_NESTED_DEPTH";
const MAX_NESTED_DEPTH: u32 = 8;

#[pyclass(name = "RunRecord")]
#[derive(Clone)]
pub struct PyRunRecord {
    record: rlab_core::RunRecord,
}

#[pymethods]
impl PyRunRecord {
    #[getter]
    pub fn run_id(&self) -> String {
        self.record.run_id.clone()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, self.record.path.clone())
    }

    #[getter]
    pub fn manifest(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &Value::Object(self.record.manifest.clone()))
    }

    #[getter]
    pub fn params(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &Value::Object(self.record.params.clone()))
    }

    #[getter]
    pub fn metrics(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &Value::Object(self.record.metrics.clone()))
    }
}

impl From<rlab_core::RunRecord> for PyRunRecord {
    fn from(record: rlab_core::RunRecord) -> Self {
        Self { record }
    }
}

#[pyclass(name = "RunQuery")]
pub struct PyRunQuery {
    root: PathBuf,
}

#[pyclass(name = "RunHandle", frozen)]
pub struct PyRunHandle {
    run_id: String,
    path: PathBuf,
}

#[pymethods]
impl PyRunHandle {
    #[getter]
    pub fn run_id(&self) -> String {
        self.run_id.clone()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, self.path.clone())
    }

    #[getter]
    pub fn status(&self) -> PyResult<String> {
        Ok(run_json(&self.path)?
            .get("status")
            .and_then(Value::as_str)
            .unwrap_or("unknown")
            .to_string())
    }

    #[getter]
    pub fn result(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &read_json_or(&self.path.join("results.json"), Value::Null)?,
        )
    }

    pub fn metrics(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &read_json_or(
                &self.path.join("metrics_summary.json"),
                Value::Object(Default::default()),
            )?,
        )
    }

    pub fn artifact(&self, py: Python<'_>, name: &str) -> PyResult<PyObject> {
        for artifact in read_jsonl(&self.path.join("artifacts").join("artifacts.jsonl"))? {
            if artifact.get("name").and_then(Value::as_str) == Some(name) {
                let Some(path) = artifact.get("path").and_then(Value::as_str) else {
                    return Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "artifact {name:?} has no path"
                    )));
                };
                return py_path(py, PathBuf::from(path));
            }
        }
        Err(pyo3::exceptions::PyKeyError::new_err(format!(
            "artifact not found: {name}"
        )))
    }
}

#[pymethods]
impl PyRunQuery {
    #[new]
    #[pyo3(signature = (root=None))]
    pub fn new(root: Option<PathBuf>) -> Self {
        Self {
            root: root.unwrap_or_else(|| PathBuf::from(".rlab/runs")),
        }
    }

    #[getter]
    pub fn root(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, self.root.clone())
    }

    #[pyo3(signature = (*, target=None, seed=None))]
    pub fn find(&self, target: Option<String>, seed: Option<i64>) -> PyResult<Vec<PyRunRecord>> {
        rlab_core::query_run_records(&self.root, target.as_deref(), seed)
            .map(|records| records.into_iter().map(PyRunRecord::from).collect())
            .map_err(to_py_error)
    }

    pub fn all(&self) -> PyResult<Vec<PyRunRecord>> {
        rlab_core::all_run_records(&self.root)
            .map(|records| records.into_iter().map(PyRunRecord::from).collect())
            .map_err(to_py_error)
    }
}

#[pyclass(name = "RuntimeContext")]
pub struct PyRuntimeContext {
    run_id: Option<String>,
    run_dir: Option<PathBuf>,
    cache_dir: Option<PathBuf>,
    project_root: PathBuf,
    params: Py<PyDict>,
    seed: Option<u64>,
    strict: bool,
    metrics: BTreeMap<String, f64>,
    artifacts: Vec<Value>,
    logs: Vec<String>,
}

#[pymethods]
impl PyRuntimeContext {
    #[new]
    #[pyo3(signature = (run_id=None, run_dir=None, cache_dir=None, project_root=None, params_json="{}", seed=None, strict=false))]
    pub fn new(
        py: Python<'_>,
        run_id: Option<String>,
        run_dir: Option<PathBuf>,
        cache_dir: Option<PathBuf>,
        project_root: Option<PathBuf>,
        params_json: &str,
        seed: Option<u64>,
        strict: bool,
    ) -> PyResult<Self> {
        Ok(Self {
            run_id,
            run_dir,
            cache_dir,
            project_root: project_root.unwrap_or_else(|| PathBuf::from(".")),
            params: py
                .import_bound("json")?
                .call_method1("loads", (params_json,))?
                .downcast_into::<PyDict>()?
                .unbind(),
            seed,
            strict,
            metrics: BTreeMap::new(),
            artifacts: Vec::new(),
            logs: Vec::new(),
        })
    }

    pub fn log_metric(&mut self, name: String, value: f64) {
        self.metrics.insert(name, value);
    }

    pub fn log_metrics(&mut self, metrics: BTreeMap<String, f64>) {
        self.metrics.extend(metrics);
    }

    pub fn metrics_json(&self) -> PyResult<String> {
        to_json(&self.metrics)
    }

    pub fn artifacts_json(&self) -> PyResult<String> {
        to_json(&self.artifacts)
    }

    pub fn logs_json(&self) -> PyResult<String> {
        to_json(&self.logs)
    }

    pub fn host_event_lines(
        &self,
        py: Python<'_>,
        request_id: &str,
        result: PyObject,
    ) -> PyResult<Vec<String>> {
        let result = py_to_json(py, result)?;
        rlab_core::host::event_lines(&rlab_core::host::execution_events(
            request_id,
            &self.metrics,
            &self.artifacts,
            &self.logs,
            result,
        ))
        .map_err(to_py_error)
    }

    pub fn params_json(&self, py: Python<'_>) -> PyResult<String> {
        to_json(&py_to_json(py, self.params.clone_ref(py).into())?)
    }

    #[pyo3(signature = (name, default=None))]
    pub fn str_param(
        &self,
        py: Python<'_>,
        name: &str,
        default: Option<String>,
    ) -> PyResult<String> {
        match self.param_obj(py, name)? {
            Some(value) => value.extract(),
            None => default.ok_or_else(|| param_type_error(name, "string")),
        }
        .map_err(|_| param_type_error(name, "string"))
    }

    #[pyo3(signature = (name, default=None))]
    pub fn int_param(&self, py: Python<'_>, name: &str, default: Option<i64>) -> PyResult<i64> {
        match self.param_obj(py, name)? {
            Some(value) if value.extract::<bool>().is_ok() => {
                Err(param_type_error(name, "integer"))
            }
            Some(value) => value
                .extract()
                .map_err(|_| param_type_error(name, "integer")),
            None => default.ok_or_else(|| param_type_error(name, "integer")),
        }
    }

    pub fn optional_int_param(&self, py: Python<'_>, name: &str) -> PyResult<Option<i64>> {
        match self.param_obj(py, name)? {
            None => Ok(None),
            Some(value) if value.is_none() => Ok(None),
            Some(value) if value.extract::<bool>().is_ok() => {
                Err(param_type_error(name, "integer"))
            }
            Some(value) => value
                .extract()
                .map(Some)
                .map_err(|_| param_type_error(name, "integer")),
        }
    }

    #[pyo3(signature = (name, default=None))]
    pub fn number_param(&self, py: Python<'_>, name: &str, default: Option<f64>) -> PyResult<f64> {
        match self.param_obj(py, name)? {
            Some(value) if value.extract::<bool>().is_ok() => {
                Err(param_type_error(name, "numeric"))
            }
            Some(value) => value
                .extract()
                .map_err(|_| param_type_error(name, "numeric")),
            None => default.ok_or_else(|| param_type_error(name, "numeric")),
        }
    }

    #[pyo3(signature = (name, default=None))]
    pub fn bool_param(&self, py: Python<'_>, name: &str, default: Option<bool>) -> PyResult<bool> {
        match self.param_obj(py, name)? {
            Some(value) => value
                .extract()
                .map_err(|_| param_type_error(name, "boolean")),
            None => default.ok_or_else(|| param_type_error(name, "boolean")),
        }
    }

    #[pyo3(signature = (name, default=None))]
    pub fn path_param(
        &self,
        py: Python<'_>,
        name: &str,
        default: Option<PathBuf>,
    ) -> PyResult<PyObject> {
        let path = match self.param_obj(py, name)? {
            Some(value) => self.resolve_project_path(value.extract()?),
            None => default
                .map(|path| self.resolve_project_path(path))
                .ok_or_else(|| param_type_error(name, "path"))?,
        };
        py_path(py, path)
    }

    pub fn output_path(&self, py: Python<'_>, value: PathBuf) -> PyResult<PyObject> {
        py_path(py, self.output_pathbuf(value)?)
    }

    #[pyo3(signature = (exclude=None, path_prefix=None, passthrough_roots=None))]
    pub fn overrides(
        &self,
        py: Python<'_>,
        exclude: Option<Vec<String>>,
        path_prefix: Option<String>,
        passthrough_roots: Option<Vec<String>>,
    ) -> PyResult<PyObject> {
        let Value::Object(params) = py_to_json(py, self.params.clone_ref(py).into())? else {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "runtime params must be an object",
            ));
        };
        let excluded = exclude.unwrap_or_default();
        let passthrough = passthrough_roots.unwrap_or_default();
        let mut result = serde_json::Map::new();
        for (key, value) in params {
            if excluded.iter().any(|item| item == &key) {
                continue;
            }
            let root = key.split('.').next().unwrap_or(&key);
            let output_key = match &path_prefix {
                Some(prefix) if !passthrough.iter().any(|item| item == root) => {
                    format!("{prefix}.{key}")
                }
                _ => key,
            };
            result.insert(output_key, value);
        }
        py_from_json(py, &Value::Object(result))
    }

    #[pyo3(signature = (schema, base, *, exclude=None, path_prefix=None, passthrough_roots=None, strict=false))]
    pub fn config(
        &self,
        py: Python<'_>,
        schema: PyObject,
        base: PyObject,
        exclude: Option<Vec<String>>,
        path_prefix: Option<String>,
        passthrough_roots: Option<Vec<String>>,
        strict: bool,
    ) -> PyResult<PyObject> {
        let base_value = py_to_json(py, base)?;
        if !base_value.is_object() {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "base config must serialize to a JSON object",
            ));
        }
        let overrides = self.overrides(py, exclude, path_prefix, passthrough_roots)?;
        let kwargs = PyDict::new_bound(py);
        kwargs.set_item("strict", strict)?;
        let resolved = py
            .import_bound("rlab")?
            .getattr("apply_overrides")?
            .call((py_from_json(py, &base_value)?, overrides), Some(&kwargs))?;
        Ok(schema
            .bind(py)
            .getattr("model_validate")?
            .call1((resolved,))?
            .unbind())
    }

    #[pyo3(signature = (first, second=None, kind="file", version="1", metadata=None, inputs=None))]
    pub fn save_artifact(
        &mut self,
        py: Python<'_>,
        first: PyObject,
        second: Option<PyObject>,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
        inputs: Option<Vec<String>>,
    ) -> PyResult<PyObject> {
        let (name, path) = self.artifact_args(py, first, second)?;
        if !path.exists() {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "artifact path does not exist: {}",
                path.display()
            )));
        }
        self.record_artifact(py, &name, &path, kind, version, metadata, inputs)?;
        py_path(py, path)
    }

    pub fn save_file(&mut self, py: Python<'_>, name: &str, path: PathBuf) -> PyResult<PyObject> {
        let path = self.resolve_project_path(path);
        if !path.is_file() {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "artifact file does not exist: {}",
                path.display()
            )));
        }
        self.record_artifact(py, name, &path, "file", "1", None, None)?;
        py_path(py, path)
    }

    pub fn save_dir(&mut self, py: Python<'_>, name: &str, path: PathBuf) -> PyResult<PyObject> {
        let path = self.resolve_project_path(path);
        if !path.is_dir() {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "artifact directory does not exist: {}",
                path.display()
            )));
        }
        self.record_artifact(py, name, &path, "directory", "1", None, None)?;
        py_path(py, path)
    }

    #[pyo3(signature = (name, payload, *, artifact=None, kind="file"))]
    pub fn write_manifest(
        &mut self,
        py: Python<'_>,
        name: PathBuf,
        payload: PyObject,
        artifact: Option<String>,
        kind: &str,
    ) -> PyResult<PyObject> {
        let path = self.output_pathbuf(name.clone())?;
        let value = py_to_json(py, payload)?;
        if !value.is_object() {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "manifest payload must be a JSON object",
            ));
        }
        rlab_core::fs::write_json_atomic(&path, &value).map_err(to_py_error)?;
        let artifact_name = artifact.unwrap_or_else(|| {
            name.to_string_lossy()
                .replace(std::path::MAIN_SEPARATOR, ".")
        });
        self.record_artifact(py, &artifact_name, &path, kind, "1", None, None)?;
        py_path(py, path)
    }

    pub fn save_table(&mut self, py: Python<'_>, name: &str, rows: PyObject) -> PyResult<PyObject> {
        let Some(run_dir) = &self.run_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no run_dir",
            ));
        };
        let path = run_dir
            .join("artifacts")
            .join("tables")
            .join(format!("{}.json", safe_name(name)));
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let value = py_to_json(py, rows)?;
        rlab_core::fs::write_json_atomic(&path, &value).map_err(to_py_error)?;
        self.record_artifact(py, name, &path, "table", "1", None, None)?;
        py_path(py, path)
    }

    pub fn note(&mut self, text: &str) {
        self.logs.push(text.to_string());
    }

    pub fn log(&mut self, py: Python<'_>, text: &str) -> PyResult<()> {
        write_host_event(
            py,
            HostEvent::Log(LogEvent {
                protocol_version: ProtocolVersion::current(),
                request_id: self.run_id.as_deref().unwrap_or("unknown").to_string(),
                message: text.to_string(),
            }),
        )
    }

    #[pyo3(signature = (phase, component = "", state = "running", processed = 0, total = None, detail = "", unit = "", message = ""))]
    pub fn report_progress(
        &self,
        py: Python<'_>,
        phase: &str,
        component: &str,
        state: &str,
        processed: u64,
        total: Option<u64>,
        detail: &str,
        unit: &str,
        message: &str,
    ) -> PyResult<()> {
        let event = HostEvent::Progress(ProgressEvent {
            protocol_version: ProtocolVersion::current(),
            request_id: self.run_id.as_deref().unwrap_or("unknown").to_string(),
            phase: phase.to_string(),
            component: component.to_string(),
            state: state.to_string(),
            processed,
            total,
            unit: unit.to_string(),
            message: message.to_string(),
            detail: detail.to_string(),
        });
        write_host_event(py, event)
    }

    #[pyo3(signature = (target, params=None, *, seed=None, strict=None, allow_failure=false))]
    pub fn run(
        &mut self,
        py: Python<'_>,
        target: &str,
        params: Option<PyObject>,
        seed: Option<u64>,
        strict: Option<bool>,
        allow_failure: bool,
    ) -> PyResult<PyRunHandle> {
        let Some(run_dir) = &self.run_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no run_dir",
            ));
        };
        let runs_root = run_dir
            .parent()
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("run_dir has no parent"))?
            .to_path_buf();
        let before = run_ids(&runs_root)?;
        let params_value = match params {
            Some(value) => py_to_json(py, value)?,
            None => Value::Object(Default::default()),
        };
        if !params_value.is_object() {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "nested run params must be an object",
            ));
        }
        let depth = nested_depth()?;
        if depth >= MAX_NESTED_DEPTH {
            return Err(pyo3::exceptions::PyRecursionError::new_err(format!(
                "rlab nested run depth exceeded {MAX_NESTED_DEPTH}"
            )));
        }
        let executable: String = py.import_bound("sys")?.getattr("executable")?.extract()?;
        let mut command = Command::new(executable);
        command
            .arg("-m")
            .arg("rlab")
            .arg("run")
            .arg(target)
            .arg("--param")
            .arg(to_json(&params_value)?)
            .current_dir(&self.project_root)
            .env(ENV_NESTED_DEPTH, (depth + 1).to_string());
        if let Some(parent) = &self.run_id {
            command.env(ENV_PARENT_RUN_ID, parent);
        }
        command.env(ENV_PARENT_TARGET, target);
        if strict.unwrap_or(self.strict) {
            command.arg("--strict");
        }
        if let Some(seed) = seed {
            command.arg("--seed").arg(seed.to_string());
        }
        let output = command.output()?;
        let after = run_ids(&runs_root)?;
        let created = after
            .difference(&before)
            .map(String::to_owned)
            .collect::<Vec<_>>();
        if created.len() != 1 {
            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "nested run expected exactly one child run, found {}",
                created.len()
            )));
        }
        let child = PyRunHandle {
            run_id: created[0].clone(),
            path: runs_root.join(&created[0]),
        };
        self.record_child_run(target, &child)?;
        if !output.status.success() && !allow_failure {
            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "nested run {target} failed: {}{}",
                String::from_utf8_lossy(&output.stdout),
                String::from_utf8_lossy(&output.stderr)
            )));
        }
        if child.status()? == "failed" && !allow_failure {
            return Err(pyo3::exceptions::PyRuntimeError::new_err(format!(
                "nested run {target} failed: {}",
                child.run_id
            )));
        }
        Ok(child)
    }

    #[pyo3(signature = (name_or_command, command=None))]
    pub fn run_external(
        &mut self,
        py: Python<'_>,
        name_or_command: PyObject,
        command: Option<PyObject>,
    ) -> PyResult<PyExternalResult> {
        let (name, command) = match command {
            Some(command) => (
                name_or_command.extract::<String>(py)?,
                command.bind(py).extract::<PyRef<'_, PyExternalCommand>>()?,
            ),
            None => (
                "external".to_string(),
                name_or_command
                    .bind(py)
                    .extract::<PyRef<'_, PyExternalCommand>>()?,
            ),
        };
        let Some(run_dir) = &self.run_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no run_dir",
            ));
        };
        let output_dir = run_dir.join("external").join(safe_name(&name));
        std::fs::create_dir_all(&output_dir)?;

        let stdout_path = output_dir.join("stdout.txt");
        let stderr_path = output_dir.join("stderr.txt");
        let mut core = command.core_command();
        core.stdout_path = Some(stdout_path.clone());
        core.stderr_path = Some(stderr_path.clone());
        let result =
            rlab_core::run_external_command(&core, rlab_core::ExternalRunnerKind::Subprocess)
                .map_err(to_py_error)?;
        let py_result = PyExternalResult::new(result.clone());

        self.record_artifact(
            py,
            &format!("{name}.stdout"),
            &stdout_path,
            "log",
            "1",
            None,
            None,
        )?;
        self.record_artifact(
            py,
            &format!("{name}.stderr"),
            &stderr_path,
            "log",
            "1",
            None,
            None,
        )?;
        if let Some(root) = command.output_root_path() {
            self.register_external_artifacts(py, &name, &root, &command.artifact_patterns())?;
        }
        if result.timed_out || result.exit_code.unwrap_or(1) != 0 {
            let error = py
                .import_bound("rlab.external")?
                .getattr("ExternalCommandError")?
                .call1((name, py_result.clone()))?;
            return Err(PyErr::from_value_bound(error));
        }
        Ok(py_result)
    }

    #[pyo3(signature = (name, spec, params=None))]
    pub fn external_workspace(
        &self,
        py: Python<'_>,
        name: &str,
        spec: &PyExternalWorkspace,
        params: Option<PyObject>,
    ) -> PyResult<PyObject> {
        let Some(run_dir) = &self.run_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no run_dir",
            ));
        };
        let Some(cache_dir) = &self.cache_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no cache_dir",
            ));
        };
        spec.validate()?;
        let params_value = match params {
            Some(value) => py_to_json(py, value)?,
            None => py_to_json(py, self.params.clone_ref(py).into())?,
        };
        let external_root = run_dir.join("external").join(safe_name(name));
        let outputs = external_root.join("outputs");
        let workspace = external_root.join("workspace");
        materialize_workspace(
            &self.project_root,
            cache_dir,
            &workspace,
            &outputs,
            name,
            spec,
            &params_value,
        )?;
        py.import_bound("rlab.external")?
            .getattr("AdapterContext")?
            .call1((
                py_path(py, self.project_root.clone())?,
                py_path(py, workspace)?,
                py_path(py, outputs)?,
                py_from_json(py, &params_value)?,
            ))
            .map(Bound::unbind)
    }

    #[getter]
    pub fn params(&self, py: Python<'_>) -> PyObject {
        self.params.clone_ref(py).into()
    }

    #[getter]
    pub fn output_dir(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        let Some(run_dir) = &self.run_dir else {
            return Ok(None);
        };
        let output = run_dir.join("outputs");
        std::fs::create_dir_all(&output)?;
        Ok(Some(py_path(py, output)?))
    }

    #[getter]
    pub fn run_id(&self) -> Option<String> {
        self.run_id.clone()
    }

    #[getter]
    pub fn run_dir(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        self.run_dir
            .clone()
            .map(|path| py_path(py, path))
            .transpose()
    }

    #[getter]
    pub fn cache_dir(&self, py: Python<'_>) -> PyResult<Option<PyObject>> {
        self.cache_dir
            .clone()
            .map(|path| py_path(py, path))
            .transpose()
    }

    #[getter]
    pub fn project_root(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, self.project_root.clone())
    }

    #[getter]
    pub fn seed(&self) -> Option<u64> {
        self.seed
    }
}

impl PyRuntimeContext {
    fn param_obj<'py>(&self, py: Python<'py>, name: &str) -> PyResult<Option<Bound<'py, PyAny>>> {
        self.params.bind(py).get_item(name)
    }

    fn resolve_project_path(&self, path: PathBuf) -> PathBuf {
        if path.is_absolute() {
            path
        } else {
            self.project_root.join(path)
        }
    }

    fn output_pathbuf(&self, value: PathBuf) -> PyResult<PathBuf> {
        let Some(run_dir) = &self.run_dir else {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "runtime context has no run_dir",
            ));
        };
        let output = run_dir.join("outputs").join(safe_relative_path(value)?);
        if let Some(parent) = output.parent() {
            std::fs::create_dir_all(parent)?;
        }
        Ok(output)
    }

    fn artifact_args(
        &self,
        py: Python<'_>,
        first: PyObject,
        second: Option<PyObject>,
    ) -> PyResult<(String, PathBuf)> {
        let Some(second) = second else {
            let path = self.resolve_project_path(first.extract::<PathBuf>(py)?);
            return Ok((artifact_name(&path), path));
        };
        if let Ok(name) = first.extract::<String>(py) {
            if let Ok(path) = second.extract::<PathBuf>(py) {
                return Ok((name, self.resolve_project_path(path)));
            }
        }
        let path = self.resolve_project_path(first.extract::<PathBuf>(py)?);
        let name = second
            .extract::<String>(py)
            .unwrap_or_else(|_| artifact_name(&path));
        Ok((name, path))
    }

    fn record_artifact(
        &mut self,
        py: Python<'_>,
        name: &str,
        path: &PathBuf,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
        inputs: Option<Vec<String>>,
    ) -> PyResult<()> {
        self.artifacts.push(json!({
            "schema_version": 1,
            "path": path,
            "name": name,
            "kind": kind,
            "version": version,
            "metadata": match metadata {
                Some(value) => py_to_json(py, value)?,
                None => json!({}),
            },
            "inputs": inputs.unwrap_or_default(),
        }));
        Ok(())
    }

    fn register_external_artifacts(
        &mut self,
        py: Python<'_>,
        name: &str,
        root: &PathBuf,
        patterns: &[String],
    ) -> PyResult<()> {
        if patterns.is_empty() || !root.exists() {
            return Ok(());
        }
        for path in files_below(root)? {
            let relative = path.strip_prefix(root).unwrap_or(&path);
            if patterns
                .iter()
                .any(|pattern| matches_artifact_pattern(relative, pattern))
            {
                let artifact = format!("{}.{}", name, artifact_stem(relative));
                self.record_artifact(py, &artifact, &path, "file", "1", None, None)?;
            }
        }
        Ok(())
    }

    fn record_child_run(&self, target: &str, child: &PyRunHandle) -> PyResult<()> {
        let Some(run_dir) = &self.run_dir else {
            return Ok(());
        };
        let path = run_dir.join(CHILD_RUNS_FILE);
        let entry = json!({
            "schema_version": 1,
            "target": target,
            "run_id": child.run_id,
            "path": child.path,
            "status": child.status()?,
        });
        let line = serde_json::to_string(&entry).map_err(py_json_error)?;
        use std::io::Write;
        let mut file = fs::OpenOptions::new()
            .create(true)
            .append(true)
            .open(&path)?;
        writeln!(file, "{line}")?;
        Ok(())
    }
}

#[pyfunction(name = "_failed_host_event_line")]
pub fn failed_host_event_line(
    request_id: &str,
    kind: &str,
    message: &str,
    safe_traceback: &str,
    source: &str,
) -> PyResult<String> {
    rlab_core::host::event_lines(&[rlab_core::host::failed_event(
        request_id,
        kind,
        message,
        safe_traceback,
        source,
    )])
    .map(|mut lines| lines.remove(0))
    .map_err(to_py_error)
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}

fn py_to_json(py: Python<'_>, value: PyObject) -> PyResult<Value> {
    let coerced = py
        .import_bound("rlab._typing")?
        .getattr("coerce_json_value")?
        .call1((value,))?;
    let raw: String = py
        .import_bound("json")?
        .call_method1("dumps", (coerced,))?
        .extract()?;
    from_json_str(&raw)
}

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}

fn write_host_event(py: Python<'_>, event: HostEvent) -> PyResult<()> {
    let line = serde_json::to_string(&event)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    let sys = py.import_bound("sys")?;
    let stdout = sys.getattr("stdout")?;
    stdout.call_method1("write", (format!("{line}\n"),))?;
    stdout.call_method0("flush")?;
    Ok(())
}

fn run_ids(root: &Path) -> PyResult<BTreeSet<String>> {
    if !root.exists() {
        return Ok(BTreeSet::new());
    }
    let mut values = BTreeSet::new();
    for entry in fs::read_dir(root)? {
        let path = entry?.path();
        if path.is_dir() && path.join("run.json").is_file() {
            if let Some(name) = path.file_name().and_then(|value| value.to_str()) {
                values.insert(name.to_string());
            }
        }
    }
    Ok(values)
}

fn nested_depth() -> PyResult<u32> {
    match std::env::var(ENV_NESTED_DEPTH) {
        Ok(value) => value.parse::<u32>().map_err(|_| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "{ENV_NESTED_DEPTH} must be an integer"
            ))
        }),
        Err(_) => Ok(0),
    }
}

fn run_json(path: &Path) -> PyResult<Value> {
    read_json_or(&path.join("run.json"), Value::Object(Default::default()))
}

fn read_json_or(path: &Path, default: Value) -> PyResult<Value> {
    if !path.exists() {
        return Ok(default);
    }
    let text = fs::read_to_string(path)?;
    serde_json::from_str(&text).map_err(py_json_error)
}

fn read_jsonl(path: &Path) -> PyResult<Vec<Value>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let file = fs::File::open(path)?;
    let reader = BufReader::new(file);
    let mut values = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        values.push(serde_json::from_str(&line).map_err(py_json_error)?);
    }
    Ok(values)
}

fn py_json_error(error: serde_json::Error) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(error.to_string())
}

fn param_type_error(name: &str, kind: &str) -> PyErr {
    pyo3::exceptions::PyTypeError::new_err(format!("parameter {name:?} must be {kind}"))
}

fn artifact_name(path: &Path) -> String {
    path.file_name()
        .map(|value| value.to_string_lossy().to_string())
        .unwrap_or_else(|| "artifact".to_string())
}

fn artifact_stem(path: &Path) -> String {
    safe_name(
        &path
            .with_extension("")
            .to_string_lossy()
            .replace(std::path::MAIN_SEPARATOR, "."),
    )
}

fn safe_name(value: &str) -> String {
    let cleaned = value
        .chars()
        .map(|ch| {
            if ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.') {
                ch
            } else {
                '_'
            }
        })
        .collect::<String>();
    cleaned.trim_matches(['.', '_']).to_string()
}

fn safe_relative_path(value: PathBuf) -> PyResult<PathBuf> {
    if value.is_absolute()
        || value
            .components()
            .any(|part| matches!(part, std::path::Component::ParentDir))
    {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "path must be relative and stay inside the run directory",
        ));
    }
    Ok(value)
}

fn files_below(root: &Path) -> PyResult<Vec<PathBuf>> {
    let mut files = Vec::new();
    collect_files(root, &mut files)?;
    Ok(files)
}

fn collect_files(path: &Path, files: &mut Vec<PathBuf>) -> PyResult<()> {
    if path.is_file() {
        files.push(path.to_path_buf());
        return Ok(());
    }
    if path.is_dir() {
        for entry in std::fs::read_dir(path)? {
            collect_files(&entry?.path(), files)?;
        }
    }
    Ok(())
}

fn matches_artifact_pattern(relative: &Path, pattern: &str) -> bool {
    let value = relative.to_string_lossy();
    let filename = relative
        .file_name()
        .map(|name| name.to_string_lossy())
        .unwrap_or_default();
    if let Some(suffix) = pattern.strip_prefix("**/*") {
        return filename.ends_with(suffix);
    }
    if let Some(suffix) = pattern.strip_prefix("**/") {
        return value.ends_with(suffix) || filename == suffix;
    }
    value == pattern
}

fn materialize_workspace(
    project_root: &Path,
    cache_dir: &Path,
    workspace: &Path,
    outputs: &Path,
    name: &str,
    spec: &PyExternalWorkspace,
    params: &Value,
) -> PyResult<()> {
    std::fs::create_dir_all(outputs)?;
    if !workspace.exists() {
        let source = resolve_workspace_source(project_root, spec, params)?;
        copy_workspace_source(&source, workspace, spec)?;
        link_cached_paths(cache_dir, name, &source, workspace, spec)?;
    }
    link_output_paths(workspace, outputs, spec)?;
    Ok(())
}

fn resolve_workspace_source(
    project_root: &Path,
    spec: &PyExternalWorkspace,
    params: &Value,
) -> PyResult<PathBuf> {
    let source = params
        .get(spec.source_param_ref())
        .and_then(Value::as_str)
        .unwrap_or_else(|| spec.default_source_ref());
    let path = PathBuf::from(source);
    let path = if path.is_absolute() {
        path
    } else {
        project_root.join(path)
    };
    if !path.is_dir() {
        return Err(pyo3::exceptions::PyFileNotFoundError::new_err(format!(
            "external workspace source does not exist: {}",
            path.display()
        )));
    }
    Ok(path)
}

fn copy_workspace_source(
    source: &Path,
    workspace: &Path,
    spec: &PyExternalWorkspace,
) -> PyResult<()> {
    if workspace.exists() {
        return Ok(());
    }
    let temporary =
        workspace.with_extension(format!("tmp.{}.{}", std::process::id(), unique_nanos()));
    if temporary.exists() {
        remove_existing(&temporary)?;
    }
    copy_dir_filtered(source, &temporary, source, spec)?;
    match std::fs::rename(&temporary, workspace) {
        Ok(()) => Ok(()),
        Err(_) if workspace.exists() => {
            remove_existing(&temporary)?;
            Ok(())
        }
        Err(error) => Err(error.into()),
    }
}

fn copy_dir_filtered(
    root: &Path,
    source: &Path,
    base: &Path,
    spec: &PyExternalWorkspace,
) -> PyResult<()> {
    std::fs::create_dir_all(source)?;
    for entry in std::fs::read_dir(root)? {
        let entry = entry?;
        let path = entry.path();
        let relative = path.strip_prefix(base).unwrap_or(&path);
        let name = entry.file_name().to_string_lossy().to_string();
        let file_type = entry.file_type()?;
        if spec.ignored_paths().iter().any(|ignored| ignored == &name)
            || excluded_workspace_path(relative, spec)
        {
            continue;
        }
        let target = source.join(relative);
        if file_type.is_symlink() {
            copy_symlink(&path, &target)?;
        } else if file_type.is_dir() {
            copy_dir_filtered(&path, source, base, spec)?;
        } else if file_type.is_file() {
            if let Some(parent) = target.parent() {
                std::fs::create_dir_all(parent)?;
            }
            std::fs::copy(&path, target)?;
        }
    }
    Ok(())
}

fn excluded_workspace_path(relative: &Path, spec: &PyExternalWorkspace) -> bool {
    spec.cached_paths()
        .iter()
        .chain(spec.output_paths())
        .any(|item| relative == Path::new(item.path_ref()))
}

fn link_cached_paths(
    cache_dir: &Path,
    name: &str,
    source: &Path,
    workspace: &Path,
    spec: &PyExternalWorkspace,
) -> PyResult<()> {
    let cache_root = cache_dir.join(safe_name(name)).join("resources");
    for item in spec.cached_paths() {
        let relative = safe_relative_path(PathBuf::from(item.path_ref()))?;
        let target = cache_root.join(safe_name(item.name_ref()));
        if !target.exists() {
            copy_path_or_dir(&source.join(&relative), &target)?;
        }
        replace_with_symlink(&workspace.join(relative), &target)?;
    }
    Ok(())
}

fn link_output_paths(workspace: &Path, outputs: &Path, spec: &PyExternalWorkspace) -> PyResult<()> {
    for item in spec.output_paths() {
        let relative = safe_relative_path(PathBuf::from(item.path_ref()))?;
        let target = outputs.join(safe_relative_path(PathBuf::from(item.name_ref()))?);
        std::fs::create_dir_all(&target)?;
        replace_with_symlink(&workspace.join(relative), &target)?;
    }
    Ok(())
}

fn copy_path_or_dir(source: &Path, target: &Path) -> PyResult<()> {
    let metadata = match std::fs::symlink_metadata(source) {
        Ok(metadata) => metadata,
        Err(_) => {
            std::fs::create_dir_all(target)?;
            return Ok(());
        }
    };
    let file_type = metadata.file_type();
    if file_type.is_symlink() {
        copy_symlink(source, target)
    } else if file_type.is_dir() {
        copy_dir_all(source, target)
    } else if file_type.is_file() {
        if let Some(parent) = target.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::copy(source, target)?;
        Ok(())
    } else {
        std::fs::create_dir_all(target)?;
        Ok(())
    }
}

fn copy_dir_all(source: &Path, target: &Path) -> PyResult<()> {
    std::fs::create_dir_all(target)?;
    for entry in std::fs::read_dir(source)? {
        let entry = entry?;
        let path = entry.path();
        let destination = target.join(entry.file_name());
        let file_type = entry.file_type()?;
        if file_type.is_symlink() {
            copy_symlink(&path, &destination)?;
        } else if file_type.is_dir() {
            copy_dir_all(&path, &destination)?;
        } else if file_type.is_file() {
            std::fs::copy(&path, destination)?;
        }
    }
    Ok(())
}

fn copy_symlink(source: &Path, target: &Path) -> PyResult<()> {
    let link = std::fs::read_link(source)?;
    if let Some(parent) = target.parent() {
        std::fs::create_dir_all(parent)?;
    }
    #[cfg(unix)]
    std::os::unix::fs::symlink(link, target)?;
    Ok(())
}

fn replace_with_symlink(link: &Path, target: &Path) -> PyResult<()> {
    if let Some(parent) = link.parent() {
        std::fs::create_dir_all(parent)?;
    }
    if link.exists() || link.is_symlink() {
        remove_existing(link)?;
    }
    #[cfg(unix)]
    std::os::unix::fs::symlink(target, link)?;
    Ok(())
}

fn remove_existing(path: &Path) -> PyResult<()> {
    if path.is_dir() && !path.is_symlink() {
        std::fs::remove_dir_all(path)?;
    } else if path.exists() || path.is_symlink() {
        std::fs::remove_file(path)?;
    }
    Ok(())
}

fn unique_nanos() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or_default()
}

#[pyclass(name = "RunDirectory")]
#[derive(Clone)]
pub struct PyRunDirectory {
    id: String,
}

#[pymethods]
impl PyRunDirectory {
    #[new]
    pub fn new(id: String) -> Self {
        Self { id }
    }

    #[getter]
    pub fn id(&self) -> String {
        self.id.clone()
    }
}
