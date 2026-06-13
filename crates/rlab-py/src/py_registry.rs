use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use serde_json::Value;

use crate::convert::json::{from_json_str, to_json, to_pretty_json};
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
        let record = rlab_core::RegistryRecord::from_spec(rlab_core::RegistryRecordSpec {
            kind: parse_registry_kind(kind)?,
            name: name.to_owned(),
            version: version.to_owned(),
            module: module.to_owned(),
            qualname: qualname.to_owned(),
            source,
            tags: tags.unwrap_or_default(),
            description: description.to_owned(),
            metadata: parse_metadata(metadata)?,
        });

        validate_record(&record)?;

        Ok(Self { inner: record })
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.inner.kind.as_str().to_string()
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name.clone()
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner)
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
        Self {
            inner: rlab_core::Registry::new(),
        }
    }

    pub fn insert(&mut self, record: &PyRegistryRecord) -> PyResult<()> {
        self.inner.insert(record.inner.clone()).map_err(to_py_error)
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&self.inner)
    }
}

fn parse_registry_kind(kind: &str) -> PyResult<rlab_core::RegistryKind> {
    rlab_core::RegistryKind::parse(kind).map_err(to_py_error)
}

fn parse_metadata(metadata: Option<String>) -> PyResult<BTreeMap<String, Value>> {
    match metadata {
        Some(value) => from_json_str(&value),
        None => Ok(BTreeMap::new()),
    }
}

fn validate_record(record: &rlab_core::RegistryRecord) -> PyResult<()> {
    rlab_core::registry::validate_registry_record(record).map_err(to_py_error)
}
