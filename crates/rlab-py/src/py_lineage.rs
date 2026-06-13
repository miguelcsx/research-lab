use std::collections::HashMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use rlab_core::{add_lineage_edge_at_root, lineage_for_at_root};

use crate::error::to_py_error;

#[pyfunction(name = "add_lineage_edge")]
#[pyo3(signature = (root, source, target, reason=None))]
pub fn add_lineage_edge_py(
    root: PathBuf,
    source: &str,
    target: &str,
    reason: Option<&str>,
) -> PyResult<()> {
    add_lineage_edge_at_root(&root, source, target, reason.map(str::to_owned))
        .map(|_| ())
        .map_err(to_py_error)
}

#[pyfunction(name = "lineage_for")]
pub fn lineage_for_py(root: PathBuf, reference: &str) -> PyResult<HashMap<String, Vec<String>>> {
    let report = lineage_for_at_root(&root, reference).map_err(to_py_error)?;
    Ok(HashMap::from([
        ("upstream".to_owned(), report.upstream),
        ("downstream".to_owned(), report.downstream),
    ]))
}
