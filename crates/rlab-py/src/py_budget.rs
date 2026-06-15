use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "BudgetEstimate")]
#[derive(Clone)]
pub struct PyBudgetEstimate {
    estimate: rlab_core::BudgetEstimate,
}

#[pymethods]
impl PyBudgetEstimate {
    #[getter]
    pub fn jobs(&self) -> u64 {
        self.estimate.jobs
    }

    #[getter]
    pub fn total_seconds(&self) -> f64 {
        self.estimate.total_seconds
    }

    #[getter]
    pub fn total_storage_gb(&self) -> f64 {
        self.estimate.total_storage_gb
    }
}

impl From<rlab_core::BudgetEstimate> for PyBudgetEstimate {
    fn from(estimate: rlab_core::BudgetEstimate) -> Self {
        Self { estimate }
    }
}

#[pyfunction(name = "estimate_budget")]
pub fn estimate_budget_py(
    jobs: u64,
    seconds_per_job: f64,
    storage_gb_per_job: f64,
) -> PyResult<PyBudgetEstimate> {
    rlab_core::estimate_budget(jobs, seconds_per_job, storage_gb_per_job)
        .map(PyBudgetEstimate::from)
        .map_err(to_py_error)
}

#[pyfunction(name = "estimate_required_repetitions")]
pub fn estimate_required_repetitions_py(
    effect_size: f64,
    variance: f64,
    alpha: f64,
    power: f64,
) -> PyResult<u64> {
    rlab_core::estimate_required_repetitions(effect_size, variance, alpha, power)
        .map_err(to_py_error)
}
