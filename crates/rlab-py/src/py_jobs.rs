use std::path::PathBuf;

use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "JobRecord")]
#[derive(Clone)]
pub struct PyJobRecord {
    record: rlab_core::JobRecord,
}

#[pymethods]
impl PyJobRecord {
    #[new]
    #[pyo3(signature = (id, command, status, log_path, exit_code=None))]
    pub fn new(
        id: String,
        command: String,
        status: &str,
        log_path: PathBuf,
        exit_code: Option<i32>,
    ) -> PyResult<Self> {
        let status = rlab_core::JobStatus::parse(status).map_err(to_py_error)?;
        rlab_core::JobRecord::new(
            id,
            command,
            status,
            log_path.to_string_lossy().to_string(),
            exit_code,
        )
        .map(|record| Self { record })
        .map_err(to_py_error)
    }

    #[getter]
    pub fn id(&self) -> String {
        self.record.id.clone()
    }

    #[getter]
    pub fn command(&self) -> String {
        self.record.command.clone()
    }

    #[getter]
    pub fn status(&self) -> String {
        self.record.status.as_str().to_string()
    }

    #[getter]
    pub fn log_path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, PathBuf::from(&self.record.log_path))
    }

    #[getter]
    pub fn exit_code(&self) -> Option<i32> {
        self.record.exit_code
    }
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}
