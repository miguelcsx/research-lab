use std::path::PathBuf;

use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "ArtifactManifest")]
#[derive(Clone)]
pub struct PyArtifactManifest {
    inner: rlab_core::ArtifactManifest,
}

#[pymethods]
impl PyArtifactManifest {
    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.inner).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }
}

#[pyclass(name = "ArtifactStore")]
pub struct PyArtifactStore {
    root: PathBuf,
}

#[pymethods]
impl PyArtifactStore {
    #[new]
    pub fn new(root: PathBuf) -> Self { Self { root } }

    pub fn promote(&self, source: PathBuf, kind: String, name: String, version: String) -> PyResult<PyArtifactManifest> {
        let config = rlab_core::load_effective_config(Some(&self.root), &[]).map_err(to_py_error)?;
        let paths = rlab_core::ProjectPaths::from_config(&config).map_err(to_py_error)?;
        let manifest = rlab_core::ArtifactStore::new(&paths)
            .promote(rlab_core::PromoteRequest { source, artifact_kind: kind, name, version, alias: None })
            .map_err(to_py_error)?;
        Ok(PyArtifactManifest { inner: manifest })
    }
}
