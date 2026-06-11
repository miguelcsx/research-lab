use std::path::{Path, PathBuf};

use pyo3::prelude::*;

use crate::convert::json::to_pretty_json;
use crate::error::to_py_error;

#[pyclass(name = "ArtifactManifest")]
#[derive(Clone)]
pub struct PyArtifactManifest {
    inner: rlab_core::ArtifactManifest,
}

#[pymethods]
impl PyArtifactManifest {
    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&self.inner)
    }
}

#[pyclass(name = "ArtifactStore")]
pub struct PyArtifactStore {
    root: PathBuf,
}

#[pymethods]
impl PyArtifactStore {
    #[new]
    pub fn new(root: PathBuf) -> Self {
        Self { root }
    }

    pub fn promote(
        &self,
        source: PathBuf,
        kind: String,
        name: String,
        version: String,
    ) -> PyResult<PyArtifactManifest> {
        let store = artifact_store_for_root(&self.root)?;
        let manifest = store
            .promote(promote_request(source, kind, name, version))
            .map_err(to_py_error)?;

        Ok(PyArtifactManifest { inner: manifest })
    }
}

fn artifact_store_for_root(root: &Path) -> PyResult<rlab_core::ArtifactStore> {
    let config = rlab_core::load_effective_config(Some(root), &[]).map_err(to_py_error)?;
    let paths = rlab_core::ProjectPaths::from_config(&config).map_err(to_py_error)?;

    Ok(rlab_core::ArtifactStore::new(&paths))
}

fn promote_request(
    source: PathBuf,
    kind: String,
    name: String,
    version: String,
) -> rlab_core::PromoteRequest {
    rlab_core::PromoteRequest {
        source,
        artifact_kind: kind,
        name,
        version,
        alias: None,
    }
}
