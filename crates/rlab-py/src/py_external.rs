use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use rlab_core::{run_external_command, ExternalCommand, ExternalRunnerKind};

use crate::convert::json::{to_json, to_pretty_json};
use crate::error::to_py_error;

const PATH_PARENT: &str = "..";

#[pyclass(name = "ExternalPath", frozen)]
#[derive(Clone)]
pub struct PyExternalPath {
    path: String,
    name: String,
}

#[pymethods]
impl PyExternalPath {
    #[new]
    pub fn new(path: String, name: String) -> PyResult<Self> {
        validate_relative(&path, "external path")?;
        validate_relative(&name, "managed path name")?;
        Ok(Self { path, name })
    }

    #[getter]
    pub fn path(&self) -> String {
        self.path.clone()
    }

    #[getter]
    pub fn name(&self) -> String {
        self.name.clone()
    }

    pub fn validate(&self) -> PyResult<()> {
        validate_relative(&self.path, "external path")?;
        validate_relative(&self.name, "managed path name")
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&serde_json::json!({ "path": self.path, "name": self.name }))
    }
}

#[pyclass(name = "ExternalWorkspace", frozen)]
#[derive(Clone)]
pub struct PyExternalWorkspace {
    source_param: String,
    default_source: String,
    ignored: Vec<String>,
    cached: Vec<PyExternalPath>,
    outputs: Vec<PyExternalPath>,
}

#[pymethods]
impl PyExternalWorkspace {
    #[new]
    #[pyo3(signature = (source_param, default_source, ignored=None, cached=None, outputs=None))]
    pub fn new(
        source_param: String,
        default_source: String,
        ignored: Option<Vec<String>>,
        cached: Option<Vec<PyRef<'_, PyExternalPath>>>,
        outputs: Option<Vec<PyRef<'_, PyExternalPath>>>,
    ) -> PyResult<Self> {
        let workspace = Self {
            source_param,
            default_source,
            ignored: ignored.unwrap_or_default(),
            cached: cached
                .unwrap_or_default()
                .into_iter()
                .map(|path| path.clone())
                .collect(),
            outputs: outputs
                .unwrap_or_default()
                .into_iter()
                .map(|path| path.clone())
                .collect(),
        };
        workspace.validate()?;
        Ok(workspace)
    }

    #[getter]
    pub fn source_param(&self) -> String {
        self.source_param.clone()
    }

    #[getter]
    pub fn default_source(&self) -> String {
        self.default_source.clone()
    }

    #[getter]
    pub fn ignored(&self) -> Vec<String> {
        self.ignored.clone()
    }

    #[getter]
    pub fn cached(&self) -> Vec<PyExternalPath> {
        self.cached.clone()
    }

    #[getter]
    pub fn outputs(&self) -> Vec<PyExternalPath> {
        self.outputs.clone()
    }

    pub fn validate(&self) -> PyResult<()> {
        require_text(&self.source_param, "workspace source_param cannot be empty")?;
        require_text(
            &self.default_source,
            "workspace default_source cannot be empty",
        )?;
        for path in self.cached.iter().chain(self.outputs.iter()) {
            path.validate()?;
        }
        require_unique(
            self.cached
                .iter()
                .chain(self.outputs.iter())
                .map(|path| path.path.as_str()),
            "workspace paths must be unique",
        )?;
        require_unique(
            self.cached.iter().map(|path| path.name.as_str()),
            "cached path names must be unique",
        )?;
        require_unique(
            self.outputs.iter().map(|path| path.name.as_str()),
            "output path names must be unique",
        )
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&serde_json::json!({
            "source_param": self.source_param,
            "default_source": self.default_source,
            "ignored": self.ignored,
            "cached": self.cached.iter().map(path_json).collect::<Vec<_>>(),
            "outputs": self.outputs.iter().map(path_json).collect::<Vec<_>>(),
        }))
    }
}

#[pyclass(name = "ExternalCommand", frozen)]
#[derive(Clone)]
pub struct PyExternalCommand {
    args: Vec<String>,
    cwd: Option<PathBuf>,
    env: BTreeMap<String, String>,
    timeout_seconds: Option<u64>,
    output_root: Option<PathBuf>,
    artifacts: Vec<String>,
}

#[pymethods]
impl PyExternalCommand {
    #[new]
    #[pyo3(signature = (args, cwd=None, env=None, timeout_seconds=None, output_root=None, artifacts=None))]
    pub fn new(
        args: Vec<String>,
        cwd: Option<PathBuf>,
        env: Option<BTreeMap<String, String>>,
        timeout_seconds: Option<u64>,
        output_root: Option<PathBuf>,
        artifacts: Option<Vec<String>>,
    ) -> PyResult<Self> {
        let command = Self {
            args,
            cwd,
            env: env.unwrap_or_default(),
            timeout_seconds,
            output_root,
            artifacts: artifacts.unwrap_or_default(),
        };
        command.validate()?;
        Ok(command)
    }

    #[getter]
    pub fn args(&self) -> Vec<String> {
        self.args.clone()
    }

    #[getter]
    pub fn cwd(&self) -> Option<PathBuf> {
        self.cwd.clone()
    }

    #[getter]
    pub fn env(&self) -> BTreeMap<String, String> {
        self.env.clone()
    }

    #[getter]
    pub fn timeout_seconds(&self) -> Option<u64> {
        self.timeout_seconds
    }

    #[getter]
    pub fn output_root(&self) -> Option<PathBuf> {
        self.output_root.clone()
    }

    #[getter]
    pub fn artifacts(&self) -> Vec<String> {
        self.artifacts.clone()
    }

    pub fn validate(&self) -> PyResult<()> {
        let Some(program) = self.args.first() else {
            return Err(validation_error(
                "external command requires at least one program argument",
            ));
        };
        require_text(
            program,
            "external command requires at least one program argument",
        )?;
        if self.timeout_seconds == Some(0) {
            return Err(validation_error("timeout_seconds must be positive"));
        }
        if !self.artifacts.is_empty() && self.output_root.is_none() {
            return Err(validation_error(
                "artifact patterns require an external command output_root",
            ));
        }
        for pattern in &self.artifacts {
            validate_relative(pattern, "artifact pattern")?;
        }
        Ok(())
    }

    pub fn run(&self) -> PyResult<PyExternalResult> {
        let inner = run_external_command(&self.core_command(), ExternalRunnerKind::Subprocess)
            .map_err(to_py_error)?;
        Ok(PyExternalResult { inner })
    }

    #[pyo3(signature = (args=None, cwd=None, env=None, timeout_seconds=None, output_root=None, artifacts=None))]
    pub fn replace(
        &self,
        args: Option<Vec<String>>,
        cwd: Option<PathBuf>,
        env: Option<BTreeMap<String, String>>,
        timeout_seconds: Option<u64>,
        output_root: Option<PathBuf>,
        artifacts: Option<Vec<String>>,
    ) -> PyResult<Self> {
        Self::new(
            args.unwrap_or_else(|| self.args.clone()),
            cwd.or_else(|| self.cwd.clone()),
            env.or_else(|| Some(self.env.clone())),
            timeout_seconds.or(self.timeout_seconds),
            output_root.or_else(|| self.output_root.clone()),
            artifacts.or_else(|| Some(self.artifacts.clone())),
        )
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&serde_json::json!({
            "args": self.args,
            "cwd": self.cwd,
            "env": self.env,
            "timeout_seconds": self.timeout_seconds,
            "output_root": self.output_root,
            "artifacts": self.artifacts,
        }))
    }
}

impl PyExternalCommand {
    pub(crate) fn core_command(&self) -> ExternalCommand {
        ExternalCommand {
            schema_version: 1,
            args: self.args.clone(),
            cwd: self.cwd.clone(),
            env: self.env.clone(),
            timeout_seconds: self.timeout_seconds,
            stdout_path: self
                .output_root
                .as_ref()
                .map(|path| path.join("stdout.txt")),
            stderr_path: self
                .output_root
                .as_ref()
                .map(|path| path.join("stderr.txt")),
        }
    }

    pub(crate) fn output_root_path(&self) -> Option<PathBuf> {
        self.output_root.clone()
    }

    pub(crate) fn artifact_patterns(&self) -> Vec<String> {
        self.artifacts.clone()
    }
}

impl PyExternalWorkspace {
    pub(crate) fn source_param_ref(&self) -> &str {
        &self.source_param
    }

    pub(crate) fn default_source_ref(&self) -> &str {
        &self.default_source
    }

    pub(crate) fn ignored_paths(&self) -> &[String] {
        &self.ignored
    }

    pub(crate) fn cached_paths(&self) -> &[PyExternalPath] {
        &self.cached
    }

    pub(crate) fn output_paths(&self) -> &[PyExternalPath] {
        &self.outputs
    }
}

impl PyExternalPath {
    pub(crate) fn path_ref(&self) -> &str {
        &self.path
    }

    pub(crate) fn name_ref(&self) -> &str {
        &self.name
    }
}

#[pyclass(name = "ExternalResult", frozen)]
#[derive(Clone)]
pub struct PyExternalResult {
    inner: rlab_core::ExternalResult,
}

impl PyExternalResult {
    pub(crate) fn new(inner: rlab_core::ExternalResult) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyExternalResult {
    #[getter]
    pub fn exit_code(&self) -> Option<i32> {
        self.inner.exit_code
    }

    #[getter]
    pub fn stdout(&self) -> String {
        self.inner.stdout.clone()
    }

    #[getter]
    pub fn stderr(&self) -> String {
        self.inner.stderr.clone()
    }

    #[getter]
    pub fn timed_out(&self) -> bool {
        self.inner.timed_out
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner)
    }
}

#[pyfunction(name = "run_external_command")]
#[pyo3(signature = (
    args,
    cwd=None,
    env=None,
    timeout_seconds=None,
    stdout_path=None,
    stderr_path=None
))]
pub fn run_external_command_py(
    args: Vec<String>,
    cwd: Option<PathBuf>,
    env: Option<BTreeMap<String, String>>,
    timeout_seconds: Option<u64>,
    stdout_path: Option<PathBuf>,
    stderr_path: Option<PathBuf>,
) -> PyResult<String> {
    let command = ExternalCommand {
        schema_version: 1,
        args,
        cwd,
        env: env.unwrap_or_default(),
        timeout_seconds,
        stdout_path,
        stderr_path,
    };
    let result =
        run_external_command(&command, ExternalRunnerKind::Subprocess).map_err(to_py_error)?;
    serde_json::to_string(&result).map_err(|error| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "failed to serialize external result: {error}"
        ))
    })
}

fn path_json(path: &PyExternalPath) -> serde_json::Value {
    serde_json::json!({ "path": path.path, "name": path.name })
}

fn require_text(value: &str, message: &str) -> PyResult<()> {
    if value.trim().is_empty() {
        Err(validation_error(message))
    } else {
        Ok(())
    }
}

fn validate_relative(value: &str, label: &str) -> PyResult<()> {
    require_text(value, &format!("{label} must be a non-empty relative path"))?;
    let path = std::path::Path::new(value);
    if path.is_absolute()
        || path
            .components()
            .any(|part| part.as_os_str() == PATH_PARENT)
    {
        return Err(validation_error(&format!(
            "{label} must be a non-empty relative path"
        )));
    }
    Ok(())
}

fn require_unique<'a, I>(values: I, message: &str) -> PyResult<()>
where
    I: IntoIterator<Item = &'a str>,
{
    let mut seen = std::collections::BTreeSet::new();
    for value in values {
        if !seen.insert(value) {
            return Err(validation_error(message));
        }
    }
    Ok(())
}

fn validation_error(message: &str) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(message.to_string())
}
