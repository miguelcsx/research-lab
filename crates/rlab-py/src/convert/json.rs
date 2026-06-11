use pyo3::prelude::*;
use serde::de::DeserializeOwned;
use serde::Serialize;

pub fn to_json<T>(value: &T) -> PyResult<String>
where
    T: Serialize,
{
    serde_json::to_string(value).map_err(py_value_error)
}

pub fn to_pretty_json<T>(value: &T) -> PyResult<String>
where
    T: Serialize,
{
    serde_json::to_string_pretty(value).map_err(py_value_error)
}

pub fn from_json_str<T>(value: &str) -> PyResult<T>
where
    T: DeserializeOwned,
{
    serde_json::from_str(value).map_err(py_value_error)
}

pub fn json_string_literal(value: &str) -> PyResult<String> {
    serde_json::to_string(value).map_err(py_value_error)
}

pub fn py_value_error(error: serde_json::Error) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(error.to_string())
}
