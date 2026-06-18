use std::collections::BTreeMap;
use std::fs;
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

#[pyfunction(name = "apply_overrides")]
#[pyo3(signature = (value, overrides, *, strict=false))]
pub fn apply_overrides_py(
    py: Python<'_>,
    value: PyObject,
    overrides: PyObject,
    strict: bool,
) -> PyResult<PyObject> {
    let mut value = py_to_json(py, value)?;
    if !value.is_object() {
        return Err(pyo3::exceptions::PyTypeError::new_err(
            "override target must be a JSON object",
        ));
    }
    let overrides_value = py_to_json(py, overrides)?;
    let overrides = match overrides_value {
        serde_json::Value::Object(map) => map.into_iter().collect(),
        _ => {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "overrides must be a JSON object",
            ))
        }
    };
    rlab_core::apply_dotted_overrides(&mut value, &overrides, strict).map_err(to_py_error)?;
    py_from_json(py, &value)
}

#[pyfunction(name = "read_json_manifest")]
#[pyo3(signature = (path, *, required_fields=None, schema=None))]
pub fn read_json_manifest_py(
    py: Python<'_>,
    path: PathBuf,
    required_fields: Option<Vec<String>>,
    schema: Option<Py<PyAny>>,
) -> PyResult<PyObject> {
    let raw = fs::read_to_string(&path).map_err(|error| {
        pyo3::exceptions::PyOSError::new_err(format!(
            "failed to read manifest {}: {error}",
            path.display()
        ))
    })?;
    let value: serde_json::Value = from_json_str(&raw)?;
    let object = value.as_object().ok_or_else(|| {
        pyo3::exceptions::PyTypeError::new_err(format!(
            "manifest {} must be a JSON object",
            path.display()
        ))
    })?;
    let missing: Vec<String> = required_fields
        .unwrap_or_default()
        .into_iter()
        .filter(|field| !object.contains_key(field))
        .collect();
    if !missing.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "manifest {} is missing required fields: {:?}",
            path.display(),
            missing
        )));
    }
    let resolved = py_from_json(py, &value)?;
    match schema {
        Some(schema) => Ok(schema
            .bind(py)
            .getattr("model_validate")?
            .call1((resolved,))?
            .unbind()),
        None => Ok(resolved),
    }
}

fn py_to_json(py: Python<'_>, value: PyObject) -> PyResult<serde_json::Value> {
    let coerced = py
        .import_bound("rlab._typing")?
        .getattr("coerce_json_value")?
        .call1((value,))?;
    let raw: String = py
        .import_bound("json")?
        .call_method1("dumps", (coerced,))?
        .extract()?;
    from_json_str(&raw)
}

fn py_from_json(py: Python<'_>, value: &serde_json::Value) -> PyResult<PyObject> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}
