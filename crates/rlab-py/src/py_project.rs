use pyo3::prelude::*;

#[pyclass(name = "ProjectCore")]
#[derive(Clone)]
pub struct PyProjectCore {
    name: String,
}

#[pymethods]
impl PyProjectCore {
    #[new]
    pub fn new(name: String) -> Self {
        Self { name }
    }

    #[getter]
    pub fn name(&self) -> String {
        self.name.clone()
    }
}
