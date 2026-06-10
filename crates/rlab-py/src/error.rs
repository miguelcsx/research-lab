use pyo3::exceptions::PyRuntimeError;
use pyo3::PyErr;

use rlab_core::RlabError;

pub fn to_py_error(error: RlabError) -> PyErr {
    PyRuntimeError::new_err(error.to_string())
}
