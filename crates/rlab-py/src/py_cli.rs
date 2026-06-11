use std::ffi::OsString;

use pyo3::prelude::*;

use crate::error::to_py_error;

const CLI_BINARY_NAME: &str = "rlab";

#[pyfunction]
pub fn cli_main(py: Python<'_>) -> PyResult<u8> {
    let argv = python_argv(py)?;
    let effective_args = effective_cli_args(argv);

    rlab_cli::run_from_iter(effective_args).map_err(to_py_error)
}

fn python_argv(py: Python<'_>) -> PyResult<Vec<String>> {
    py.import_bound("sys")?.getattr("argv")?.extract()
}

fn effective_cli_args(argv: Vec<String>) -> Vec<OsString> {
    std::iter::once(OsString::from(CLI_BINARY_NAME))
        .chain(user_cli_args(argv))
        .collect()
}

fn user_cli_args(argv: Vec<String>) -> impl Iterator<Item = OsString> {
    argv.into_iter().skip(1).map(OsString::from)
}
