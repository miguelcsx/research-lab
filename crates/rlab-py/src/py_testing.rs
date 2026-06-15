use std::path::PathBuf;

use pyo3::prelude::*;

#[pyfunction(name = "assert_valid_run_dir")]
pub fn assert_valid_run_dir_py(path: PathBuf) -> PyResult<()> {
    rlab_core::assert_valid_run_dir(&path).map_err(assertion_error)
}

#[pyfunction(name = "assert_metric_exists")]
pub fn assert_metric_exists_py(path: PathBuf, name: &str) -> PyResult<()> {
    rlab_core::assert_run_metric_exists(&path, name).map_err(assertion_error)
}

fn assertion_error(error: rlab_core::RlabError) -> PyErr {
    pyo3::exceptions::PyAssertionError::new_err(error.to_string())
}
