use std::collections::BTreeMap;

use pyo3::prelude::*;

fn parse_direction(direction: Option<String>) -> PyResult<Option<rlab_core::MetricDirection>> {
    match direction.as_deref() {
        None => Ok(None),
        Some(s) => {
            let json = format!("\"{}\"", s);
            serde_json::from_str::<rlab_core::MetricDirection>(&json)
                .map(Some)
                .map_err(|_| pyo3::exceptions::PyValueError::new_err(
                    format!("invalid metric direction: {s}; expected minimize, maximize, or neutral"),
                ))
        }
    }
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
    pub fn new(name: String, value: f64, unit: Option<String>, direction: Option<String>) -> PyResult<Self> {
        let direction = parse_direction(direction)?;
        Ok(Self { inner: rlab_core::Metric::new(name, value, unit, direction) })
    }

    #[getter]
    pub fn name(&self) -> String { self.inner.name.clone() }
    #[getter]
    pub fn value(&self) -> f64 { self.inner.value }
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
        Self { inner: rlab_core::ResultBundle::empty() }
    }

    pub fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner).map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))
    }
}

#[pyfunction]
pub fn bundle_from_metrics(metrics: BTreeMap<String, f64>) -> PyResult<PyResultBundle> {
    Ok(PyResultBundle { inner: rlab_core::ResultBundle::from_metric_map(metrics) })
}
