use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use pyo3::prelude::*;
use serde_json::Value;

use crate::convert::json::{from_json_str, to_json};
use crate::error::to_py_error;
const DEFAULT_VERSION: &str = "1";
#[pyclass(name = "ProjectCore")]
pub struct PyProjectCore {
    name: String,
    root: PathBuf,
    registry: rlab_core::Registry,
    callables: BTreeMap<String, Py<PyAny>>,
    params_types: BTreeMap<String, Py<PyAny>>,
}

#[pymethods]
impl PyProjectCore {
    #[new]
    #[pyo3(signature = (name, root=None))]
    pub fn new(py: Python<'_>, name: String, root: Option<PathBuf>) -> PyResult<Self> {
        let core = Self {
            name,
            root: root.unwrap_or_else(|| PathBuf::from(".")),
            registry: rlab_core::Registry::new(),
            callables: BTreeMap::new(),
            params_types: BTreeMap::new(),
        };
        let _ = py;
        Ok(core)
    }

    #[getter]
    pub fn name(&self) -> String {
        self.name.clone()
    }

    #[getter]
    pub fn root(&self) -> PathBuf {
        self.root.clone()
    }

    #[allow(clippy::too_many_arguments)]
    #[pyo3(signature = (
        kind,
        name,
        module,
        qualname,
        source,
        description,
        metadata_json,
        callable,
        version=DEFAULT_VERSION,
        tags=None,
    ))]
    pub fn register(
        &mut self,
        py: Python<'_>,
        kind: &str,
        name: &str,
        module: &str,
        qualname: &str,
        source: PathBuf,
        description: &str,
        metadata_json: &str,
        callable: Py<PyAny>,
        version: &str,
        tags: Option<Vec<String>>,
    ) -> PyResult<()> {
        let metadata = parse_metadata(metadata_json)?;
        let record = self.record(
            kind,
            name,
            module,
            qualname,
            source,
            description,
            metadata,
            version,
            tags,
        )?;
        self.insert_record(py, record, callable)
    }

    #[pyo3(signature = (kind, name, param_type=None))]
    pub fn set_params_type(
        &mut self,
        kind: &str,
        name: &str,
        param_type: Option<Py<PyAny>>,
    ) {
        let key = registry_key(kind, name);
        if let Some(param_type) = param_type {
            self.params_types.insert(key, param_type);
        }
    }

    pub fn bind_callable(&mut self, kind: &str, name: &str, callable: Py<PyAny>) {
        self.callables.insert(registry_key(kind, name), callable);
    }

    pub fn records_json(&self) -> PyResult<String> {
        to_json(&self.registry.records)
    }

    pub fn record_json(&self, kind: &str, name: &str) -> PyResult<String> {
        let kind = rlab_core::RegistryKind::parse(kind).map_err(to_py_error)?;
        let key = format!("{}:{name}", kind.as_str());
        let record = self
            .registry
            .find(kind, name)
            .ok_or_else(|| pyo3::exceptions::PyKeyError::new_err(key))?;
        to_json(record)
    }

    pub fn resolve(&self, py: Python<'_>, kind: &str, name: &str) -> PyResult<Py<PyAny>> {
        self.callables
            .get(&registry_key(kind, name))
            .map(|callable| callable.clone_ref(py))
            .ok_or_else(|| {
                pyo3::exceptions::PyKeyError::new_err(format!(
                    "no callable registered for {kind}:{name}"
                ))
            })
    }

    pub fn schema(&self, py: Python<'_>, kind: &str, name: &str) -> Option<Py<PyAny>> {
        self.params_types
            .get(&registry_key(kind, name))
            .map(|param_type| param_type.clone_ref(py))
    }

    #[pyo3(signature = (reference, overrides_json="{}", strict=false))]
    pub fn resolve_config(
        &self,
        py: Python<'_>,
        reference: &str,
        overrides_json: &str,
        strict: bool,
    ) -> PyResult<Py<PyAny>> {
        let callable = self.resolve(py, "config", reference)?;
        let base = callable.bind(py).call0()?.unbind();
        let mut value = py_to_json(py, base)?;
        if !value.is_object() {
            return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                "config:{reference} must resolve to a JSON object"
            )));
        }
        let overrides: BTreeMap<String, Value> = from_json_str(overrides_json)?;
        rlab_core::apply_dotted_overrides(&mut value, &overrides, strict).map_err(to_py_error)?;
        let resolved = py_from_json(py, &value)?;
        match self.schema(py, "config", reference) {
            Some(schema) => Ok(schema
                .bind(py)
                .getattr("model_validate")?
                .call1((resolved,))?
                .unbind()),
            None => Ok(resolved),
        }
    }
}

impl PyProjectCore {
    #[allow(clippy::too_many_arguments)]
    fn record(
        &self,
        kind: &str,
        name: &str,
        module: &str,
        qualname: &str,
        source: PathBuf,
        description: &str,
        metadata: BTreeMap<String, Value>,
        version: &str,
        tags: Option<Vec<String>>,
    ) -> PyResult<rlab_core::RegistryRecord> {
        let kind = rlab_core::RegistryKind::parse(kind).map_err(to_py_error)?;
        let record = rlab_core::RegistryRecord::from_spec(rlab_core::RegistryRecordSpec {
            kind,
            name: name.to_string(),
            version: version.to_string(),
            module: module.to_string(),
            qualname: qualname.to_string(),
            source: relative_source(&source, &self.root),
            tags: tags.unwrap_or_default(),
            description: description.to_string(),
            metadata,
        });
        rlab_core::registry::validate_registry_record(&record).map_err(to_py_error)?;
        Ok(record)
    }

    fn insert_record(
        &mut self,
        py: Python<'_>,
        record: rlab_core::RegistryRecord,
        callable: Py<PyAny>,
    ) -> PyResult<()> {
        let kind = record.kind.as_str().to_string();
        let name = record.name.clone();
        let key = registry_key(&kind, &name);

        if self.callables.contains_key(&key) {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "duplicate declaration: {kind}:{name}"
            )));
        }

        let _ = py;
        self.registry.insert(record).map_err(to_py_error)?;
        self.callables.insert(key, callable);
        Ok(())
    }
}

fn parse_metadata(metadata_json: &str) -> PyResult<BTreeMap<String, Value>> {
    from_json_str(metadata_json)
}

fn registry_key(kind: &str, name: &str) -> String {
    format!("{kind}:{name}")
}

fn relative_source(source: &Path, root: &Path) -> PathBuf {
    source
        .strip_prefix(root)
        .map(Path::to_path_buf)
        .unwrap_or_else(|_| source.to_path_buf())
}

fn py_to_json(py: Python<'_>, value: Py<PyAny>) -> PyResult<Value> {
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

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<Py<PyAny>> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}
