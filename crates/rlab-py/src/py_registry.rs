use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use serde_json::Value;

use crate::error::to_py_error;

#[pyclass(name = "RegistryRecord")]
#[derive(Clone)]
pub struct PyRegistryRecord {
    pub inner: rlab_core::RegistryRecord,
}

#[pymethods]
impl PyRegistryRecord {
    #[new]
    #[pyo3(signature = (kind, name, version, module, qualname, source, tags=None, description="", metadata=None))]
    pub fn new(
        kind: &str,
        name: &str,
        version: &str,
        module: &str,
        qualname: &str,
        source: PathBuf,
        tags: Option<Vec<String>>,
        description: &str,
        metadata: Option<String>,
    ) -> PyResult<Self> {
        let metadata_map = match metadata {
            Some(value) => serde_json::from_str::<BTreeMap<String, Value>>(&value).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?,
            None => BTreeMap::new(),
        };
        let parsed_kind = rlab_core::RegistryKind::parse(kind).map_err(to_py_error)?;
        let tag_values = tags.unwrap_or_default();
        let record = rlab_core::RegistryRecord::new(
            parsed_kind,
            name.to_string(),
            version.to_string(),
            module.to_string(),
            qualname.to_string(),
            source,
            tag_values,
            description.to_string(),
            metadata_map,
        );
        rlab_core::registry::validate_registry_record(&record).map_err(to_py_error)?;
        Ok(Self { inner: record })
    }

    #[getter]
    pub fn kind(&self) -> String { self.inner.kind.as_str().to_string() }
    #[getter]
    pub fn name(&self) -> String { self.inner.name.clone() }

    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }
}

#[pyclass(name = "Registry")]
#[derive(Clone)]
pub struct PyRegistry {
    inner: rlab_core::Registry,
}

#[pymethods]
impl PyRegistry {
    #[new]
    pub fn new() -> Self {
        Self { inner: rlab_core::Registry::new() }
    }

    pub fn insert(&mut self, record: &PyRegistryRecord) -> PyResult<()> {
        self.inner.insert(record.inner.clone()).map_err(to_py_error)
    }

    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.inner).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }
}
