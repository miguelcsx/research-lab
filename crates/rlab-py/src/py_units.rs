use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyclass(name = "Unit")]
#[derive(Clone)]
pub struct PyUnit {
    unit: rlab_core::Unit,
}

#[pymethods]
impl PyUnit {
    #[new]
    pub fn new(name: String, symbol: String, dimension: String) -> Self {
        Self {
            unit: rlab_core::Unit {
                name,
                symbol,
                dimension,
            },
        }
    }

    #[getter]
    pub fn name(&self) -> String {
        self.unit.name.clone()
    }

    #[getter]
    pub fn symbol(&self) -> String {
        self.unit.symbol.clone()
    }

    #[getter]
    pub fn dimension(&self) -> String {
        self.unit.dimension.clone()
    }
}

impl From<rlab_core::Unit> for PyUnit {
    fn from(unit: rlab_core::Unit) -> Self {
        Self { unit }
    }
}

#[pyclass(name = "UnitRegistry")]
pub struct PyUnitRegistry {
    registry: rlab_core::UnitRegistry,
}

#[pymethods]
impl PyUnitRegistry {
    #[new]
    pub fn new() -> Self {
        Self {
            registry: rlab_core::UnitRegistry::new(),
        }
    }

    pub fn add(&mut self, unit: &PyUnit) -> PyResult<()> {
        self.registry.insert(unit.unit.clone()).map_err(to_py_error)
    }

    #[getter]
    pub fn units(&self) -> std::collections::BTreeMap<String, PyUnit> {
        self.registry
            .units
            .clone()
            .into_iter()
            .map(|(symbol, unit)| (symbol, PyUnit::from(unit)))
            .collect()
    }
}

impl Default for PyUnitRegistry {
    fn default() -> Self {
        Self::new()
    }
}
