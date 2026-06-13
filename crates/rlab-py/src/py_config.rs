use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use pyo3::prelude::*;

use crate::convert::json::{from_json_str, to_json, to_pretty_json};
use crate::error::to_py_error;

#[pyclass(name = "EffectiveConfig")]
#[derive(Clone)]
pub struct PyEffectiveConfig {
    inner: rlab_core::EffectiveConfig,
}

#[pymethods]
impl PyEffectiveConfig {
    pub fn to_json(&self) -> PyResult<String> {
        to_pretty_json(&self.inner)
    }
}

#[pyfunction(name = "find_project_root")]
pub fn find_project_root_py(start: PathBuf) -> PyResult<PathBuf> {
    find_project_root(&start).map_err(to_py_error)
}

#[pyfunction(name = "load_config")]
#[pyo3(signature = (root=None))]
pub fn load_config_py(root: Option<PathBuf>) -> PyResult<PyEffectiveConfig> {
    let config = rlab_core::load_effective_config(root.as_deref(), &[]).map_err(to_py_error)?;

    Ok(PyEffectiveConfig { inner: config })
}

fn find_project_root(start: &Path) -> Result<PathBuf, rlab_core::RlabError> {
    rlab_core::find_project_root(start)
}

#[pyfunction(name = "resolve_config_document")]
#[pyo3(signature = (root, name, overrides_json="{}", suffix=".yaml", require_explicit_paths=true))]
pub fn resolve_config_document_py(
    root: PathBuf,
    name: &str,
    overrides_json: &str,
    suffix: &str,
    require_explicit_paths: bool,
) -> PyResult<String> {
    let overrides: BTreeMap<String, serde_json::Value> = from_json_str(overrides_json)?;
    let document =
        rlab_core::resolve_document(&root, name, suffix, overrides, require_explicit_paths)
            .map_err(to_py_error)?;
    to_json(&document.value)
}

#[pyfunction(name = "list_config_documents")]
#[pyo3(signature = (root, suffix=".yaml"))]
pub fn list_config_documents_py(root: PathBuf, suffix: &str) -> PyResult<Vec<String>> {
    rlab_core::list_documents(&root, suffix).map_err(to_py_error)
}

#[pyfunction(name = "validate_config_documents")]
#[pyo3(signature = (root, suffix=".yaml"))]
pub fn validate_config_documents_py(root: PathBuf, suffix: &str) -> PyResult<String> {
    to_json(&rlab_core::validate_documents(&root, suffix).map_err(to_py_error)?)
}

#[pyfunction(name = "diff_config_documents")]
pub fn diff_config_documents_py(left_json: &str, right_json: &str) -> PyResult<String> {
    let left = rlab_core::ResolvedDocument {
        name: String::new(),
        source: PathBuf::new(),
        value: from_json_str(left_json)?,
        overrides: BTreeMap::new(),
    };
    let right = rlab_core::ResolvedDocument {
        name: String::new(),
        source: PathBuf::new(),
        value: from_json_str(right_json)?,
        overrides: BTreeMap::new(),
    };
    to_json(&rlab_core::diff_documents(&left, &right))
}
