use pyo3::basic::CompareOp;
use pyo3::prelude::*;

use crate::convert::json::to_json;
use crate::error::to_py_error;

#[pyclass(name = "MetricComparison")]
#[derive(Clone)]
pub struct PyMetricComparison {
    inner: rlab_core::MetricComparison,
}

#[pymethods]
impl PyMetricComparison {
    #[getter]
    pub fn mean_a(&self) -> f64 {
        self.inner.mean_a
    }

    #[getter]
    pub fn mean_b(&self) -> f64 {
        self.inner.mean_b
    }

    #[getter]
    pub fn delta(&self) -> f64 {
        self.inner.delta
    }

    #[getter]
    pub fn effect_size(&self) -> Option<f64> {
        self.inner.effect_size
    }

    #[getter]
    pub fn confidence_interval(&self) -> Option<(f64, f64)> {
        self.inner.confidence_interval
    }

    pub fn to_json(&self) -> PyResult<String> {
        to_json(&self.inner)
    }

    fn __richcmp__(&self, other: PyRef<'_, PyMetricComparison>, op: CompareOp) -> bool {
        match op {
            CompareOp::Eq => {
                self.inner.mean_a == other.inner.mean_a
                    && self.inner.mean_b == other.inner.mean_b
                    && self.inner.delta == other.inner.delta
                    && self.inner.count_a == other.inner.count_a
                    && self.inner.count_b == other.inner.count_b
                    && self.inner.effect_size == other.inner.effect_size
                    && self.inner.confidence_interval == other.inner.confidence_interval
            }
            CompareOp::Ne => {
                self.inner.mean_a != other.inner.mean_a
                    || self.inner.mean_b != other.inner.mean_b
                    || self.inner.delta != other.inner.delta
                    || self.inner.count_a != other.inner.count_a
                    || self.inner.count_b != other.inner.count_b
                    || self.inner.effect_size != other.inner.effect_size
                    || self.inner.confidence_interval != other.inner.confidence_interval
            }
            _ => false,
        }
    }
}

#[pyfunction(name = "compare_metric_arrays")]
pub fn compare_metric_arrays_py(a: Vec<f64>, b: Vec<f64>) -> PyResult<PyMetricComparison> {
    let inner = rlab_core::compare_metric_arrays(&a, &b).map_err(to_py_error)?;
    Ok(PyMetricComparison { inner })
}

#[pyfunction(name = "paired_bootstrap")]
#[pyo3(signature = (a, b, samples=10_000, confidence=0.95, seed=0))]
pub fn paired_bootstrap_py(
    a: Vec<f64>,
    b: Vec<f64>,
    samples: usize,
    confidence: f64,
    seed: u64,
) -> PyResult<PyMetricComparison> {
    let inner =
        rlab_core::paired_bootstrap(&a, &b, samples, confidence, seed).map_err(to_py_error)?;
    Ok(PyMetricComparison { inner })
}
