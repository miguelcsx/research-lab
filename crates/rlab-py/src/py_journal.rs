use std::collections::BTreeMap;

use pyo3::prelude::*;
use serde_json::Value;
use time::{format_description::well_known::Rfc3339, OffsetDateTime};

use crate::error::to_py_error;

#[pyclass(name = "DecisionEntry")]
#[derive(Clone)]
pub struct PyDecisionEntry {
    entry: rlab_core::DecisionEntry,
}

#[pymethods]
impl PyDecisionEntry {
    #[new]
    #[pyo3(signature = (text, selected_run=None, criteria=None))]
    pub fn new(
        text: String,
        selected_run: Option<String>,
        criteria: Option<BTreeMap<String, String>>,
    ) -> Self {
        Self {
            entry: rlab_core::DecisionEntry::new(
                text,
                selected_run,
                serde_json::to_value(criteria.unwrap_or_default()).unwrap_or(Value::Null),
            ),
        }
    }

    #[getter]
    pub fn text(&self) -> String {
        self.entry.text.clone()
    }

    #[getter]
    pub fn selected_run(&self) -> Option<String> {
        self.entry.selected_run.clone()
    }

    #[getter]
    pub fn criteria(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &self.entry.criteria)
    }

    #[getter]
    pub fn created_at(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_datetime(py, self.entry.created_at)
    }
}

#[pyclass(name = "NegativeResultEntry")]
#[derive(Clone)]
pub struct PyNegativeResultEntry {
    entry: rlab_core::NegativeResultEntry,
}

#[pymethods]
impl PyNegativeResultEntry {
    #[new]
    pub fn new(hypothesis: String, tried: String, reason: String) -> Self {
        Self {
            entry: rlab_core::NegativeResultEntry::new(hypothesis, tried, reason),
        }
    }

    #[getter]
    pub fn hypothesis(&self) -> String {
        self.entry.hypothesis.clone()
    }

    #[getter]
    pub fn tried(&self) -> String {
        self.entry.tried.clone()
    }

    #[getter]
    pub fn reason(&self) -> String {
        self.entry.reason.clone()
    }

    #[getter]
    pub fn created_at(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_datetime(py, self.entry.created_at)
    }
}

#[pyclass(name = "IdeaEntry")]
#[derive(Clone)]
pub struct PyIdeaEntry {
    entry: rlab_core::IdeaEntry,
}

#[pymethods]
impl PyIdeaEntry {
    #[new]
    #[pyo3(signature = (text, status="idea"))]
    pub fn new(text: String, status: &str) -> PyResult<Self> {
        let status = rlab_core::IdeaStatus::parse(status).map_err(to_py_error)?;
        Ok(Self {
            entry: rlab_core::IdeaEntry::new(text, status),
        })
    }

    #[getter]
    pub fn id(&self) -> String {
        self.entry.id.clone()
    }

    #[getter]
    pub fn text(&self) -> String {
        self.entry.text.clone()
    }

    #[getter]
    pub fn status(&self) -> String {
        self.entry.status.as_str().to_string()
    }

    #[getter]
    pub fn created_at(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_datetime(py, self.entry.created_at)
    }
}

#[pyclass(name = "NoteEntry")]
#[derive(Clone)]
pub struct PyNoteEntry {
    entry: rlab_core::NoteEntry,
}

#[pymethods]
impl PyNoteEntry {
    #[new]
    pub fn new(run_id: String, text: String) -> Self {
        Self {
            entry: rlab_core::NoteEntry::new(run_id, text),
        }
    }

    #[getter]
    pub fn run_id(&self) -> String {
        self.entry.run_id.clone()
    }

    #[getter]
    pub fn text(&self) -> String {
        self.entry.text.clone()
    }

    #[getter]
    pub fn created_at(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_datetime(py, self.entry.created_at)
    }
}

fn py_datetime(py: Python<'_>, value: OffsetDateTime) -> PyResult<PyObject> {
    let formatted = value
        .format(&Rfc3339)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    Ok(py
        .import_bound("datetime")?
        .getattr("datetime")?
        .call_method1("fromisoformat", (formatted.replace('Z', "+00:00"),))?
        .unbind())
}

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    let raw = serde_json::to_string(value)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (raw,))?
        .unbind())
}
