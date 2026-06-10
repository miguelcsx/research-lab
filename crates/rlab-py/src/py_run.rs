use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;

#[pyclass(name = "RuntimeContext")]
pub struct PyRuntimeContext {
    run_id: Option<String>,
    run_dir: Option<PathBuf>,
    metrics: BTreeMap<String, f64>,
}

#[pymethods]
impl PyRuntimeContext {
    #[new]
    #[pyo3(signature = (run_id=None, run_dir=None))]
    pub fn new(run_id: Option<String>, run_dir: Option<PathBuf>) -> Self {
        Self { run_id, run_dir, metrics: BTreeMap::new() }
    }

    pub fn log_metric(&mut self, name: String, value: f64) {
        self.metrics.insert(name, value);
    }

    pub fn log_metrics(&mut self, metrics: BTreeMap<String, f64>) {
        for (name, value) in metrics {
            self.metrics.insert(name, value);
        }
    }

    pub fn metrics_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.metrics).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }

    #[getter]
    pub fn run_id(&self) -> Option<String> { self.run_id.clone() }
    #[getter]
    pub fn run_dir(&self) -> Option<PathBuf> { self.run_dir.clone() }
}

#[pyclass(name = "RunDirectory")]
#[derive(Clone)]
pub struct PyRunDirectory {
    id: String,
}

#[pymethods]
impl PyRunDirectory {
    #[new]
    pub fn new(id: String) -> Self { Self { id } }
    #[getter]
    pub fn id(&self) -> String { self.id.clone() }
}
