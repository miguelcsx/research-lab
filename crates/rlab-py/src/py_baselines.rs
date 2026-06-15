use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "BaselineEntry")]
#[derive(Clone)]
pub struct PyBaselineEntry {
    entry: rlab_core::BaselineEntry,
}

#[pymethods]
impl PyBaselineEntry {
    #[new]
    #[pyo3(signature = (name, metric, value, description=None))]
    pub fn new(name: String, metric: String, value: f64, description: Option<String>) -> Self {
        Self {
            entry: rlab_core::BaselineEntry::new(name, metric, value, description),
        }
    }

    #[getter]
    pub fn name(&self) -> String {
        self.entry.name.clone()
    }

    #[getter]
    pub fn metric(&self) -> String {
        self.entry.metric.clone()
    }

    #[getter]
    pub fn value(&self) -> f64 {
        self.entry.value
    }

    #[getter]
    pub fn description(&self) -> Option<String> {
        self.entry.description.clone()
    }
}

impl From<rlab_core::BaselineEntry> for PyBaselineEntry {
    fn from(entry: rlab_core::BaselineEntry) -> Self {
        Self { entry }
    }
}

#[pyclass(name = "BaselineStore")]
pub struct PyBaselineStore {
    store: rlab_core::BaselineStore,
}

#[pymethods]
impl PyBaselineStore {
    #[new]
    pub fn new() -> Self {
        Self {
            store: rlab_core::BaselineStore::new(),
        }
    }

    pub fn add(&mut self, entry: &PyBaselineEntry) -> PyResult<()> {
        self.store.insert(entry.entry.clone()).map_err(to_py_error)
    }

    pub fn list(&self) -> Vec<PyBaselineEntry> {
        self.store
            .entries
            .values()
            .cloned()
            .map(PyBaselineEntry::from)
            .collect()
    }
}

impl Default for PyBaselineStore {
    fn default() -> Self {
        Self::new()
    }
}
