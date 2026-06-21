use std::collections::BTreeMap;
use std::path::PathBuf;

use pyo3::prelude::*;
use serde_json::Value;

use crate::convert::json::{from_json_str, json_string_literal, to_json};

const METRIC_DIRECTION_ERROR_SUFFIX: &str = "expected minimize, maximize, or neutral";

fn parse_direction(direction: Option<String>) -> PyResult<Option<rlab_core::MetricDirection>> {
    direction.as_deref().map(parse_metric_direction).transpose()
}

#[pyclass(name = "Metric")]
#[derive(Clone)]
pub struct PyMetric {
    pub inner: rlab_core::Metric,
}

#[pymethods]
impl PyMetric {
    #[new]
    #[pyo3(signature = (name, value, unit=None, direction=None))]
    pub fn new(
        name: String,
        value: f64,
        unit: Option<String>,
        direction: Option<String>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: metric_from_python_args(name, value, unit, direction)?,
        })
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name.clone()
    }

    #[getter]
    pub fn value(&self) -> f64 {
        self.inner.value
    }
}

#[pyclass(name = "ResultBundle")]
#[derive(Clone)]
pub struct PyResultBundle {
    pub inner: rlab_core::ResultBundle,
}

#[pymethods]
impl PyResultBundle {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: rlab_core::ResultBundle::empty(),
        }
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner)
    }
}

#[pyclass(name = "FileArtifact")]
#[derive(Clone)]
pub struct PyFileArtifact {
    inner: rlab_core::FileArtifact,
}

#[pymethods]
impl PyFileArtifact {
    #[new]
    #[pyo3(signature = (name, path, kind="file", version="1", metadata=None))]
    pub fn new(
        py: Python<'_>,
        name: String,
        path: PathBuf,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: rlab_core::FileArtifact::new_typed(
                name,
                path,
                kind.to_string(),
                version.to_string(),
                py_metadata(py, metadata)?,
            ),
        })
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name.clone()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, self.inner.path.clone())
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.inner.kind.clone()
    }

    #[getter]
    pub fn version(&self) -> String {
        self.inner.version.clone()
    }

    #[getter]
    pub fn metadata(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &Value::Object(self.inner.metadata.clone().into_iter().collect()),
        )
    }

    pub fn to_event_payload(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &self.inner.event_payload())
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner.event_payload())
    }
}

#[pyclass(name = "FigureArtifact")]
#[derive(Clone)]
pub struct PyFigureArtifact {
    inner: PyFileArtifact,
}

#[pymethods]
impl PyFigureArtifact {
    #[new]
    #[pyo3(signature = (name, path, kind="figure", version="1", metadata=None))]
    pub fn new(
        py: Python<'_>,
        name: String,
        path: PathBuf,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: PyFileArtifact::new(py, name, path, kind, version, metadata)?,
        })
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.path(py)
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.inner.kind()
    }

    #[getter]
    pub fn version(&self) -> String {
        self.inner.version()
    }

    #[getter]
    pub fn metadata(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.metadata(py)
    }

    pub fn to_event_payload(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.to_event_payload(py)
    }

    pub fn to_json(&self) -> PyResult<String> {
        self.inner.to_json()
    }
}

#[pyclass(name = "TableArtifact")]
#[derive(Clone)]
pub struct PyTableArtifact {
    inner: PyFileArtifact,
}

#[pymethods]
impl PyTableArtifact {
    #[new]
    #[pyo3(signature = (name, path, kind="table", version="1", metadata=None))]
    pub fn new(
        py: Python<'_>,
        name: String,
        path: PathBuf,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: PyFileArtifact::new(py, name, path, kind, version, metadata)?,
        })
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.path(py)
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.inner.kind()
    }

    #[getter]
    pub fn version(&self) -> String {
        self.inner.version()
    }

    #[getter]
    pub fn metadata(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.metadata(py)
    }

    pub fn to_event_payload(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.to_event_payload(py)
    }

    pub fn to_json(&self) -> PyResult<String> {
        self.inner.to_json()
    }
}

#[pyclass(name = "LogArtifact")]
#[derive(Clone)]
pub struct PyLogArtifact {
    inner: PyFileArtifact,
}

#[pymethods]
impl PyLogArtifact {
    #[new]
    #[pyo3(signature = (name, path, kind="log", version="1", metadata=None))]
    pub fn new(
        py: Python<'_>,
        name: String,
        path: PathBuf,
        kind: &str,
        version: &str,
        metadata: Option<PyObject>,
    ) -> PyResult<Self> {
        Ok(Self {
            inner: PyFileArtifact::new(py, name, path, kind, version, metadata)?,
        })
    }

    #[getter]
    pub fn name(&self) -> String {
        self.inner.name()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.path(py)
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.inner.kind()
    }

    #[getter]
    pub fn version(&self) -> String {
        self.inner.version()
    }

    #[getter]
    pub fn metadata(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.metadata(py)
    }

    pub fn to_event_payload(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.to_event_payload(py)
    }

    pub fn to_json(&self) -> PyResult<String> {
        self.inner.to_json()
    }
}

#[pyfunction]
pub fn bundle_from_metrics(metrics: BTreeMap<String, f64>) -> PyResult<PyResultBundle> {
    Ok(PyResultBundle {
        inner: rlab_core::ResultBundle::from_metric_map(metrics),
    })
}

fn metric_from_python_args(
    name: String,
    value: f64,
    unit: Option<String>,
    direction: Option<String>,
) -> PyResult<rlab_core::Metric> {
    Ok(rlab_core::Metric::new(
        name,
        value,
        unit,
        parse_direction(direction)?,
    ))
}

fn parse_metric_direction(value: &str) -> PyResult<rlab_core::MetricDirection> {
    let encoded = json_string_literal(value)?;

    serde_json::from_str::<rlab_core::MetricDirection>(&encoded)
        .map_err(|_| invalid_metric_direction(value))
}

fn invalid_metric_direction(value: &str) -> PyErr {
    pyo3::exceptions::PyValueError::new_err(format!(
        "invalid metric direction: {value}; {METRIC_DIRECTION_ERROR_SUFFIX}"
    ))
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}

fn py_metadata(py: Python<'_>, metadata: Option<PyObject>) -> PyResult<BTreeMap<String, Value>> {
    let Some(metadata) = metadata else {
        return Ok(BTreeMap::new());
    };
    let coerced = py
        .import_bound("rlab._typing")?
        .getattr("coerce_json_value")?
        .call1((metadata,))?;
    let raw: String = py
        .import_bound("json")?
        .call_method1("dumps", (coerced,))?
        .extract()?;
    match from_json_str(&raw)? {
        Value::Object(values) => Ok(values.into_iter().collect()),
        _ => Err(pyo3::exceptions::PyTypeError::new_err(
            "artifact metadata must be a JSON object",
        )),
    }
}
