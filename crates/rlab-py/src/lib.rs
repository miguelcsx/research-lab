#![allow(clippy::useless_conversion)]
#![allow(unexpected_cfgs)]

mod convert;
mod error;
mod module;
mod py_artifact;
mod py_baselines;
mod py_budget;
mod py_cache;
mod py_cli;
mod py_config;
mod py_external;
mod py_governance;
mod py_jobs;
mod py_journal;
mod py_lineage;
mod py_project;
mod py_registry;
mod py_reports;
mod py_result;
mod py_run;
mod py_stats;
mod py_strict;
mod py_testing;
mod py_units;

use pyo3::prelude::*;

#[pymodule]
fn _rlab(py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module::register(py, module)
}
