use std::path::{Path, PathBuf};

use pyo3::prelude::*;

use crate::convert::json::to_pretty_json;
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

#[pyfunction]
pub fn find_project_root_py(start: PathBuf) -> PyResult<PathBuf> {
    find_project_root(&start).map_err(to_py_error)
}

#[pyfunction]
#[pyo3(signature = (root=None))]
pub fn load_config_py(root: Option<PathBuf>) -> PyResult<PyEffectiveConfig> {
    let config = rlab_core::load_effective_config(root.as_deref(), &[]).map_err(to_py_error)?;

    Ok(PyEffectiveConfig { inner: config })
}

fn find_project_root(start: &Path) -> Result<PathBuf, rlab_core::RlabError> {
    rlab_core::find_project_root(start)
}
