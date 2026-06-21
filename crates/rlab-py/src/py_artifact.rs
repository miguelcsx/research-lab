use std::path::{Path, PathBuf};

use pyo3::prelude::*;
use pyo3::types::PyDict;

use crate::convert::json::to_pretty_json;
use crate::error::to_py_error;

#[pyclass(name = "ArtifactManifest")]
#[derive(Clone)]
pub struct PyArtifactManifest {
    inner: rlab_core::ArtifactManifest,
}

#[pymethods]
impl PyArtifactManifest {
    #[getter]
    pub fn kind(&self) -> String {
        self.inner.reference.kind.clone()
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.reference.name.clone()
    }

    #[getter]
    pub fn version(&self) -> String {
        self.inner.reference.version.clone()
    }

    #[getter]
    pub fn sha256(&self) -> String {
        self.inner.sha256.clone()
    }

    #[getter]
    pub fn storage_type(&self) -> String {
        self.inner.storage_type.as_str().to_string()
    }

    #[getter]
    pub fn size_bytes(&self) -> u64 {
        self.inner.size_bytes
    }

    #[getter]
    pub fn object_path(&self) -> PathBuf {
        self.inner.object_path.clone()
    }

    #[getter]
    pub fn source_path(&self) -> PathBuf {
        self.inner.source_path.clone()
    }

    #[getter]
    pub fn alias(&self) -> Option<String> {
        self.inner.alias.clone()
    }

    pub fn as_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        let dict = PyDict::new_bound(py);
        dict.set_item("schema_version", self.inner.schema_version)?;
        dict.set_item("kind", self.inner.reference.kind.clone())?;
        dict.set_item("name", self.inner.reference.name.clone())?;
        dict.set_item("version", self.inner.reference.version.clone())?;
        dict.set_item("sha256", self.inner.sha256.clone())?;
        dict.set_item("storage_type", self.inner.storage_type.as_str())?;
        dict.set_item("size_bytes", self.inner.size_bytes)?;
        dict.set_item("object_path", self.inner.object_path.clone())?;
        dict.set_item("source_path", self.inner.source_path.clone())?;
        dict.set_item("alias", self.inner.alias.clone())?;
        dict.set_item("created_at", self.inner.created_at.to_string())?;
        Ok(dict.into())
    }

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

    #[pyo3(signature = (source, kind, name, version="".to_string(), alias=None))]
    pub fn promote(
        &self,
        source: PathBuf,
        kind: String,
        name: String,
        version: String,
        alias: Option<String>,
    ) -> PyResult<PyArtifactManifest> {
        let store = artifact_store_for_root(&self.root)?;
        let manifest = store
            .promote(promote_request(source, kind, name, version, alias))
            .map_err(to_py_error)?;

        Ok(PyArtifactManifest { inner: manifest })
    }

    pub fn describe(&self, reference: String) -> PyResult<PyArtifactManifest> {
        let paths = project_paths_for_root(&self.root)?;
        let manifest =
            rlab_core::describe_artifact_reference(&paths, &reference).map_err(to_py_error)?;
        Ok(PyArtifactManifest { inner: manifest })
    }

    pub fn resolve_path(&self, reference: String) -> PyResult<PathBuf> {
        Ok(self.describe(reference)?.inner.object_path)
    }

    pub fn parse_reference(&self, py: Python<'_>, reference: String) -> PyResult<PyObject> {
        let parsed = rlab_core::parse_artifact_reference(&reference).map_err(to_py_error)?;
        let dict = PyDict::new_bound(py);
        dict.set_item("kind", parsed.kind)?;
        dict.set_item("name", parsed.name)?;
        dict.set_item("version", parsed.version)?;
        Ok(dict.into())
    }
}

fn artifact_store_for_root(root: &Path) -> PyResult<rlab_core::ArtifactStore> {
    Ok(rlab_core::ArtifactStore::new(&project_paths_for_root(
        root,
    )?))
}

fn project_paths_for_root(root: &Path) -> PyResult<rlab_core::ProjectPaths> {
    let config = rlab_core::load_effective_config(Some(root), &[]).map_err(to_py_error)?;
    rlab_core::ProjectPaths::from_config(&config).map_err(to_py_error)
}

fn promote_request(
    source: PathBuf,
    kind: String,
    name: String,
    version: String,
    alias: Option<String>,
) -> rlab_core::PromoteRequest {
    rlab_core::PromoteRequest {
        source,
        artifact_kind: kind,
        name,
        version,
        alias,
    }
}
