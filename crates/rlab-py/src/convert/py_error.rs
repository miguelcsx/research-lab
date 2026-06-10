use pyo3::exceptions::{PyFileNotFoundError, PyRuntimeError, PyValueError};
use pyo3::PyErr;

use rlab_core::RlabError;

pub fn map_error(error: RlabError) -> PyErr {
    match error {
        RlabError::NotFound { subject } => PyFileNotFoundError::new_err(subject),
        RlabError::Config { message }
        | RlabError::Registry { message }
        | RlabError::Reference { message }
        | RlabError::Validation { message } => PyValueError::new_err(message),
        other => PyRuntimeError::new_err(other.to_string()),
    }
}
