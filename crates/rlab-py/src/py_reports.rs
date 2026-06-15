use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use serde_json::Value;

use crate::convert::json::from_json_str;
use crate::error::to_py_error;

#[pyfunction(name = "write_markdown_report")]
pub fn write_markdown_report_py(
    py: Python<'_>,
    path: PathBuf,
    title: &str,
    fields: PyObject,
) -> PyResult<PyObject> {
    let fields = json_map(py, fields)?;
    let path = rlab_core::write_markdown_report(&path, title, &fields).map_err(to_py_error)?;
    py_path(py, path)
}

#[pyfunction(name = "write_card")]
pub fn write_card_py(
    py: Python<'_>,
    path: PathBuf,
    title: &str,
    sections: PyObject,
) -> PyResult<PyObject> {
    let sections = json_sections(py, sections)?;
    let path = rlab_core::write_markdown_card(&path, title, &sections).map_err(to_py_error)?;
    py_path(py, path)
}

fn json_map(py: Python<'_>, value: PyObject) -> PyResult<BTreeMap<String, Value>> {
    let json = json_dumps(py, value)?;
    from_json_str(&json)
}

fn json_sections(
    py: Python<'_>,
    value: PyObject,
) -> PyResult<BTreeMap<String, BTreeMap<String, Value>>> {
    let json = json_dumps(py, value)?;
    from_json_str(&json)
}

fn json_dumps(py: Python<'_>, value: PyObject) -> PyResult<String> {
    let json = py.import_bound("json")?;
    json.call_method1("dumps", (value,))?.extract()
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}
