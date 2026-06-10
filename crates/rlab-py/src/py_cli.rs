use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyfunction]
pub fn cli_main() -> PyResult<u8> {
    rlab_cli::run_from_env().map_err(to_py_error)
}
