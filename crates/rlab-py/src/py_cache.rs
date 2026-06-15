use std::path::PathBuf;

use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "CacheEntry")]
#[derive(Clone)]
pub struct PyCacheEntry {
    entry: rlab_core::CacheEntry,
}

#[pymethods]
impl PyCacheEntry {
    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, PathBuf::from(&self.entry.path))
    }

    #[getter]
    pub fn size_bytes(&self) -> u64 {
        self.entry.bytes
    }

    #[getter]
    pub fn bytes(&self) -> u64 {
        self.entry.bytes
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.entry.kind.clone()
    }
}

impl From<rlab_core::CacheEntry> for PyCacheEntry {
    fn from(entry: rlab_core::CacheEntry) -> Self {
        Self { entry }
    }
}

#[pyfunction(name = "cache_path")]
#[pyo3(signature = (root=None))]
pub fn cache_path_py(py: Python<'_>, root: Option<PathBuf>) -> PyResult<PyObject> {
    py_path(py, project_paths(root).cache)
}

#[pyfunction(name = "list_cache")]
#[pyo3(signature = (root=None))]
pub fn list_cache_py(root: Option<PathBuf>) -> PyResult<Vec<PyCacheEntry>> {
    rlab_core::cache_list(&project_paths(root))
        .map(|entries| entries.into_iter().map(PyCacheEntry::from).collect())
        .map_err(to_py_error)
}

#[pyfunction(name = "cache_size")]
pub fn cache_size_py(entries: Vec<PyRef<'_, PyCacheEntry>>) -> u64 {
    entries.iter().map(|entry| entry.entry.bytes).sum()
}

fn project_paths(root: Option<PathBuf>) -> rlab_core::ProjectPaths {
    let root = root.unwrap_or_else(|| PathBuf::from("."));
    rlab_core::ProjectPaths {
        root: root.clone(),
        runs: root.join(".rlab/runs"),
        artifacts: root.join(".rlab/artifacts"),
        cache: root.join(".rlab/cache"),
        registry_cache: root.join(".rlab/cache/registry.json"),
    }
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}
