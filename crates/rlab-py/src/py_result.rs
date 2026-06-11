use std::collections::BTreeMap;

use pyo3::prelude::*;

use crate::convert::json::{json_string_literal, to_json};

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
