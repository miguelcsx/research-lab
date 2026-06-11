use pyo3::PyErr;

use rlab_core::RlabError;

pub fn to_py_error(error: RlabError) -> PyErr {
    crate::convert::py_error::map_error(error)
}
