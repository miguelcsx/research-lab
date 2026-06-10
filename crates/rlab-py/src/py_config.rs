use std::path::PathBuf;

use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "EffectiveConfig")]
#[derive(Clone)]
pub struct PyEffectiveConfig {
    inner: rlab_core::EffectiveConfig,
}

#[pymethods]
impl PyEffectiveConfig {
    #[getter]
    pub fn project_name(&self) -> String {
        self.inner.project.name.clone()
    }

    #[getter]
    pub fn root(&self) -> PathBuf {
        self.inner.project.root.clone()
    }

    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string_pretty(&self.inner).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }
}

#[pyfunction(name = "find_project_root")]
pub fn find_project_root_py(path: PathBuf) -> PyResult<PathBuf> {
    rlab_core::find_project_root(&path).map_err(to_py_error)
}

#[pyfunction(name = "load_config")]
#[pyo3(signature = (root=None))]
pub fn load_config_py(root: Option<PathBuf>) -> PyResult<PyEffectiveConfig> {
    let config = rlab_core::load_effective_config(root.as_deref(), &[]).map_err(to_py_error)?;
    Ok(PyEffectiveConfig { inner: config })
}
