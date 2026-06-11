use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use rlab_core::{run_external_command, ExternalCommand, ExternalRunnerKind};

use crate::error::to_py_error;

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
