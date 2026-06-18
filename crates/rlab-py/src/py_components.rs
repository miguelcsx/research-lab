use std::collections::BTreeMap;

use pyo3::basic::CompareOp;
use pyo3::prelude::*;
use pyo3::types::{PyTuple, PyType};
use serde_json::{json, Value};

use crate::convert::json::{from_json_str, to_json};

pyo3::create_exception!(
    _rlab,
    MissingRequirementsError,
    pyo3::exceptions::PyValueError
);

const REQUIREMENT_FIELDS: [&str; 5] = [
    "model_outputs",
    "model_heads",
    "batch_fields",
    "capabilities",
    "artifacts",
];

#[pyclass(name = "ComponentSpec", frozen)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PyComponentSpec {
    reference: String,
    params: BTreeMap<String, Value>,
}

#[pymethods]
impl PyComponentSpec {
    #[new]
    #[pyo3(signature = (reference, params=None))]
    pub fn new(reference: String, params: Option<PyObject>, py: Python<'_>) -> PyResult<Self> {
        Ok(Self {
            reference,
            params: match params {
                Some(params) => py_mapping_to_json_object(py, params, "component params")?,
                None => BTreeMap::new(),
            },
        })
    }

    #[classmethod]
    pub fn __class_getitem__(cls: &Bound<'_, PyType>, _item: PyObject) -> Py<PyAny> {
        cls.clone().unbind().into()
    }

    #[classmethod]
    pub fn empty(_cls: &Bound<'_, PyType>, reference: String) -> Self {
        Self {
            reference,
            params: BTreeMap::new(),
        }
    }

    #[classmethod]
    pub fn from_value(_cls: &Bound<'_, PyType>, py: Python<'_>, value: PyObject) -> PyResult<Self> {
        component_spec_from_value(py, value)
    }

    #[getter]
    pub fn r#ref(&self) -> String {
        self.reference.clone()
    }

    #[getter]
    pub fn params(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &Value::Object(self.params.clone().into_iter().collect()),
        )
    }

    #[getter]
    pub fn name(&self) -> String {
        self.reference
            .rsplit_once(':')
            .map(|(_, name)| name)
            .unwrap_or(&self.reference)
            .to_string()
    }

    #[getter]
    pub fn kind(&self) -> Option<String> {
        self.reference
            .split_once(':')
            .map(|(kind, _)| kind.to_string())
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &json!({
                "ref": self.reference,
                "params": self.params,
            }),
        )
    }

    pub fn __repr__(&self) -> String {
        format!(
            "ComponentSpec(ref={:?}, params={:?})",
            self.reference, self.params
        )
    }

    pub fn __richcmp__(&self, other: PyRef<'_, PyComponentSpec>, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == &*other),
            CompareOp::Ne => Ok(self != &*other),
            _ => Err(pyo3::exceptions::PyTypeError::new_err(
                "ComponentSpec only supports equality comparison",
            )),
        }
    }
}

#[pyclass(name = "Requirements", frozen)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PyRequirements {
    model_outputs: Vec<String>,
    model_heads: Vec<String>,
    batch_fields: Vec<String>,
    capabilities: Vec<String>,
    artifacts: Vec<String>,
}

#[pymethods]
impl PyRequirements {
    #[new]
    #[pyo3(signature = (model_outputs=None, model_heads=None, batch_fields=None, capabilities=None, artifacts=None))]
    pub fn new(
        model_outputs: Option<Vec<String>>,
        model_heads: Option<Vec<String>>,
        batch_fields: Option<Vec<String>>,
        capabilities: Option<Vec<String>>,
        artifacts: Option<Vec<String>>,
    ) -> Self {
        Self {
            model_outputs: model_outputs.unwrap_or_default(),
            model_heads: model_heads.unwrap_or_default(),
            batch_fields: batch_fields.unwrap_or_default(),
            capabilities: capabilities.unwrap_or_default(),
            artifacts: artifacts.unwrap_or_default(),
        }
    }

    #[getter]
    pub fn model_outputs(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_tuple(py, &self.model_outputs)
    }

    #[getter]
    pub fn model_heads(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_tuple(py, &self.model_heads)
    }

    #[getter]
    pub fn batch_fields(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_tuple(py, &self.batch_fields)
    }

    #[getter]
    pub fn capabilities(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_tuple(py, &self.capabilities)
    }

    #[getter]
    pub fn artifacts(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_tuple(py, &self.artifacts)
    }

    pub fn merge(&self, other: PyRef<'_, PyRequirements>) -> Self {
        self.merged(&other)
    }

    #[pyo3(signature = (*fields))]
    pub fn only(&self, fields: Vec<String>) -> Self {
        Self {
            model_outputs: selected(&self.model_outputs, &fields, "model_outputs"),
            model_heads: selected(&self.model_heads, &fields, "model_heads"),
            batch_fields: selected(&self.batch_fields, &fields, "batch_fields"),
            capabilities: selected(&self.capabilities, &fields, "capabilities"),
            artifacts: selected(&self.artifacts, &fields, "artifacts"),
        }
    }

    #[pyo3(signature = (*fields))]
    pub fn without(&self, fields: Vec<String>) -> Self {
        Self {
            model_outputs: removed(&self.model_outputs, &fields, "model_outputs"),
            model_heads: removed(&self.model_heads, &fields, "model_heads"),
            batch_fields: removed(&self.batch_fields, &fields, "batch_fields"),
            capabilities: removed(&self.capabilities, &fields, "capabilities"),
            artifacts: removed(&self.artifacts, &fields, "artifacts"),
        }
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(py, &self.to_value())
    }

    pub fn __repr__(&self) -> String {
        format!("{:?}", self)
    }

    pub fn __richcmp__(&self, other: PyRef<'_, PyRequirements>, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self == &*other),
            CompareOp::Ne => Ok(self != &*other),
            _ => Err(pyo3::exceptions::PyTypeError::new_err(
                "Requirements only supports equality comparison",
            )),
        }
    }
}

impl PyRequirements {
    fn merged(&self, other: &Self) -> Self {
        Self {
            model_outputs: union(&self.model_outputs, &other.model_outputs),
            model_heads: union(&self.model_heads, &other.model_heads),
            batch_fields: union(&self.batch_fields, &other.batch_fields),
            capabilities: union(&self.capabilities, &other.capabilities),
            artifacts: union(&self.artifacts, &other.artifacts),
        }
    }

    fn to_value(&self) -> Value {
        json!({
            "model_outputs": self.model_outputs,
            "model_heads": self.model_heads,
            "batch_fields": self.batch_fields,
            "capabilities": self.capabilities,
            "artifacts": self.artifacts,
        })
    }

    fn from_value(value: Option<&Value>) -> PyResult<Self> {
        let Some(Value::Object(map)) = value else {
            return Ok(Self::new(None, None, None, None, None));
        };
        Ok(Self {
            model_outputs: string_vec(map.get("model_outputs"), "model_outputs")?,
            model_heads: string_vec(map.get("model_heads"), "model_heads")?,
            batch_fields: string_vec(map.get("batch_fields"), "batch_fields")?,
            capabilities: string_vec(map.get("capabilities"), "capabilities")?,
            artifacts: string_vec(map.get("artifacts"), "artifacts")?,
        })
    }
}

#[pyclass(name = "ComponentContract", frozen)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PyComponentContract {
    requires: PyRequirements,
    provides: PyRequirements,
}

#[pymethods]
impl PyComponentContract {
    #[new]
    #[pyo3(signature = (requires=None, provides=None))]
    pub fn new(
        requires: Option<PyRef<'_, PyRequirements>>,
        provides: Option<PyRef<'_, PyRequirements>>,
    ) -> Self {
        Self {
            requires: requires
                .map(|value| value.clone())
                .unwrap_or_else(|| PyRequirements::new(None, None, None, None, None)),
            provides: provides
                .map(|value| value.clone())
                .unwrap_or_else(|| PyRequirements::new(None, None, None, None, None)),
        }
    }

    #[getter]
    pub fn requires(&self) -> PyRequirements {
        self.requires.clone()
    }

    #[getter]
    pub fn provides(&self) -> PyRequirements {
        self.provides.clone()
    }

    pub fn merge(&self, other: PyRef<'_, PyComponentContract>) -> Self {
        Self {
            requires: self.requires.merged(&other.requires),
            provides: self.provides.merged(&other.provides),
        }
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_from_json(
            py,
            &json!({
                "requires": self.requires.to_value(),
                "provides": self.provides.to_value(),
            }),
        )
    }
}

#[pyclass(name = "MissingRequirements", frozen)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PyMissingRequirements {
    inner: PyRequirements,
}

#[pymethods]
impl PyMissingRequirements {
    #[new]
    #[pyo3(signature = (model_outputs=None, model_heads=None, batch_fields=None, capabilities=None, artifacts=None))]
    pub fn new(
        model_outputs: Option<Vec<String>>,
        model_heads: Option<Vec<String>>,
        batch_fields: Option<Vec<String>>,
        capabilities: Option<Vec<String>>,
        artifacts: Option<Vec<String>>,
    ) -> Self {
        Self {
            inner: PyRequirements::new(
                model_outputs,
                model_heads,
                batch_fields,
                capabilities,
                artifacts,
            ),
        }
    }

    #[getter]
    pub fn model_outputs(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.model_outputs(py)
    }

    #[getter]
    pub fn model_heads(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.model_heads(py)
    }

    #[getter]
    pub fn batch_fields(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.batch_fields(py)
    }

    #[getter]
    pub fn capabilities(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.capabilities(py)
    }

    #[getter]
    pub fn artifacts(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.artifacts(py)
    }

    #[getter]
    pub fn ok(&self) -> bool {
        REQUIREMENT_FIELDS
            .iter()
            .all(|field| self.values(field).is_empty())
    }

    #[pyo3(signature = (label="component contract"))]
    pub fn raise_if_any(&self, label: &str) -> PyResult<()> {
        if self.ok() {
            return Ok(());
        }
        Err(MissingRequirementsError::new_err(format!(
            "{label} is missing requirements: {}",
            to_json(&self.inner.to_value())?
        )))
    }

    pub fn to_dict(&self, py: Python<'_>) -> PyResult<PyObject> {
        self.inner.to_dict(py)
    }
}

impl PyMissingRequirements {
    fn values(&self, field: &str) -> &[String] {
        match field {
            "model_outputs" => &self.inner.model_outputs,
            "model_heads" => &self.inner.model_heads,
            "batch_fields" => &self.inner.batch_fields,
            "capabilities" => &self.inner.capabilities,
            "artifacts" => &self.inner.artifacts,
            _ => &[],
        }
    }
}

#[pyfunction(name = "component_spec_from_value")]
pub fn component_spec_from_value_py(py: Python<'_>, value: PyObject) -> PyResult<PyComponentSpec> {
    component_spec_from_value(py, value)
}

#[pyfunction(name = "collect_requirements")]
pub fn collect_requirements_py(values: Vec<PyRef<'_, PyRequirements>>) -> PyRequirements {
    values.into_iter().fold(
        PyRequirements::new(None, None, None, None, None),
        |acc, value| acc.merge(value),
    )
}

#[pyfunction(name = "collect_contracts")]
pub fn collect_contracts_py(values: Vec<PyRef<'_, PyComponentContract>>) -> PyComponentContract {
    values.into_iter().fold(
        PyComponentContract {
            requires: PyRequirements::new(None, None, None, None, None),
            provides: PyRequirements::new(None, None, None, None, None),
        },
        |acc, value| acc.merge(value),
    )
}

#[pyfunction(name = "collect_component_requirements")]
pub fn collect_component_requirements_py(
    py: Python<'_>,
    lookup: PyObject,
    kind: String,
    specs: PyObject,
) -> PyResult<PyRequirements> {
    let mut values = Vec::new();
    for item in specs.bind(py).iter()? {
        let spec = component_spec_from_value(py, item?.unbind())?;
        let requirement = lookup
            .bind(py)
            .call1((kind.clone(), spec.name()))?
            .extract::<PyRef<'_, PyRequirements>>()?;
        values.push(requirement.clone());
    }
    Ok(values.iter().fold(
        PyRequirements::new(None, None, None, None, None),
        |acc, value| acc.merged(value),
    ))
}

#[pyfunction(name = "missing_requirements")]
#[pyo3(signature = (required, provided, *, fields=None))]
pub fn missing_requirements_py(
    required: PyRef<'_, PyRequirements>,
    provided: PyRef<'_, PyRequirements>,
    fields: Option<Vec<String>>,
) -> PyMissingRequirements {
    let selected =
        fields.unwrap_or_else(|| REQUIREMENT_FIELDS.iter().map(|v| v.to_string()).collect());
    PyMissingRequirements {
        inner: PyRequirements {
            model_outputs: missing_if_selected(
                &required.model_outputs,
                &provided.model_outputs,
                &selected,
                "model_outputs",
            ),
            model_heads: missing_if_selected(
                &required.model_heads,
                &provided.model_heads,
                &selected,
                "model_heads",
            ),
            batch_fields: missing_if_selected(
                &required.batch_fields,
                &provided.batch_fields,
                &selected,
                "batch_fields",
            ),
            capabilities: missing_if_selected(
                &required.capabilities,
                &provided.capabilities,
                &selected,
                "capabilities",
            ),
            artifacts: missing_if_selected(
                &required.artifacts,
                &provided.artifacts,
                &selected,
                "artifacts",
            ),
        },
    }
}

#[pyfunction(name = "requirements_from_mapping")]
pub fn requirements_from_mapping_py(py: Python<'_>, value: PyObject) -> PyResult<PyRequirements> {
    let value = py_to_json(py, value)?;
    PyRequirements::from_value(Some(&value))
}

fn component_spec_from_value(py: Python<'_>, value: PyObject) -> PyResult<PyComponentSpec> {
    if let Ok(spec) = value.extract::<PyRef<'_, PyComponentSpec>>(py) {
        return Ok(spec.clone());
    }
    if let Ok(reference) = value.extract::<String>(py) {
        return Ok(PyComponentSpec {
            reference,
            params: BTreeMap::new(),
        });
    }
    let value = py_to_json(py, value)?;
    let Value::Object(map) = value else {
        return Err(pyo3::exceptions::PyTypeError::new_err(
            "component spec must be a string or mapping",
        ));
    };
    let reference = map
        .get("ref")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| {
            pyo3::exceptions::PyValueError::new_err("component spec requires a non-empty ref")
        })?
        .to_string();
    let params = match map.get("params") {
        Some(Value::Object(params)) => params.clone().into_iter().collect(),
        Some(_) => {
            return Err(pyo3::exceptions::PyTypeError::new_err(
                "component spec params must be a mapping",
            ))
        }
        None => map
            .into_iter()
            .filter(|(key, _)| key.as_str() != "ref")
            .collect(),
    };
    Ok(PyComponentSpec { reference, params })
}

fn py_to_json(py: Python<'_>, value: PyObject) -> PyResult<Value> {
    let coerced = py
        .import_bound("rlab._typing")?
        .getattr("coerce_json_value")?
        .call1((value,))?;
    let raw: String = py
        .import_bound("json")?
        .call_method1("dumps", (coerced,))?
        .extract()?;
    from_json_str(&raw)
}

fn py_mapping_to_json_object(
    py: Python<'_>,
    value: PyObject,
    label: &str,
) -> PyResult<BTreeMap<String, Value>> {
    match py_to_json(py, value)? {
        Value::Object(map) => Ok(map.into_iter().collect()),
        _ => Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "{label} must be a mapping"
        ))),
    }
}

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}

fn py_tuple(py: Python<'_>, values: &[String]) -> PyResult<PyObject> {
    Ok(PyTuple::new_bound(py, values).unbind().into())
}

fn union(left: &[String], right: &[String]) -> Vec<String> {
    let mut values = left.to_vec();
    for value in right {
        if !values.contains(value) {
            values.push(value.clone());
        }
    }
    values
}

fn selected(values: &[String], fields: &[String], field: &str) -> Vec<String> {
    if fields.iter().any(|value| value == field) {
        values.to_vec()
    } else {
        Vec::new()
    }
}

fn removed(values: &[String], fields: &[String], field: &str) -> Vec<String> {
    if fields.iter().any(|value| value == field) {
        Vec::new()
    } else {
        values.to_vec()
    }
}

fn missing_if_selected(
    required: &[String],
    provided: &[String],
    fields: &[String],
    field: &str,
) -> Vec<String> {
    if !fields.iter().any(|value| value == field) {
        return Vec::new();
    }
    required
        .iter()
        .filter(|value| !provided.contains(value))
        .cloned()
        .collect()
}

fn string_vec(value: Option<&Value>, field: &str) -> PyResult<Vec<String>> {
    match value {
        None => Ok(Vec::new()),
        Some(Value::Array(values)) => values
            .iter()
            .map(|value| {
                value
                    .as_str()
                    .map(|value| value.to_string())
                    .ok_or_else(|| {
                        pyo3::exceptions::PyTypeError::new_err(format!(
                            "{field} entries must be strings"
                        ))
                    })
            })
            .collect(),
        Some(_) => Err(pyo3::exceptions::PyTypeError::new_err(format!(
            "{field} must be an array"
        ))),
    }
}
