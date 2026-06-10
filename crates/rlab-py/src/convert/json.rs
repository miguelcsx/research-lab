use pyo3::prelude::*;

pub fn py_to_json(value: &Bound<'_, PyAny>) -> PyResult<serde_json::Value> {
    let string = value.py().import_bound("json")?.call_method1("dumps", (value,))?.extract::<String>()?;
    serde_json::from_str(&string).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
}
