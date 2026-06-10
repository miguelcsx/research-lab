use std::path::PathBuf;

use pyo3::prelude::*;

pub fn extract_path(value: &Bound<'_, PyAny>) -> PyResult<PathBuf> {
    value.extract::<PathBuf>()
}
