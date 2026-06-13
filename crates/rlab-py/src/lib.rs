#![allow(clippy::useless_conversion)]

mod convert;
mod error;
mod module;
mod py_artifact;
mod py_cli;
mod py_config;
mod py_external;
mod py_lineage;
mod py_project;
mod py_registry;
mod py_result;
mod py_run;
mod py_strict;

use pyo3::prelude::*;

#[pymodule]
fn _rlab(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module::register(py, module)
}
