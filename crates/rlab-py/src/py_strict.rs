use pyo3::prelude::*;

#[pyclass(name = "ProductionPolicy")]
#[derive(Clone)]
pub struct PyProductionPolicy {
    strict: bool,
}

#[pymethods]
impl PyProductionPolicy {
    #[new]
    pub fn new(strict: bool) -> Self {
        Self { strict }
    }

    #[getter]
    pub fn strict(&self) -> bool {
        self.strict
    }
}
