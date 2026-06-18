use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde_json::Value;

use crate::convert::json::{from_json_str, to_json};
use crate::error::to_py_error;
use crate::py_data::{PyNativeDocumentAssembler, PyNativeSimhashDedup, PyNativeTextFilter};

const DEFAULT_VERSION: &str = "1";
const KEY_METADATA: &str = "metadata";
const KEY_NAME: &str = "name";
const KEY_STEPS: &str = "steps";
const KEY_STEP: &str = "step";
const KIND_WORKFLOW: &str = "workflow";
const KIND_WORKFLOW_STEP: &str = "workflow_step";
const SCHEMA_VERSION: u32 = 1;

#[pyclass(name = "ProjectCore")]
pub struct PyProjectCore {
    name: String,
    root: PathBuf,
    registry: rlab_core::Registry,
    callables: BTreeMap<String, Py<PyAny>>,
    component_schemas: BTreeMap<String, Py<PyAny>>,
    component_requirements: BTreeMap<String, String>,
}

#[pymethods]
impl PyProjectCore {
    #[new]
    #[pyo3(signature = (name, root=None))]
    pub fn new(py: Python<'_>, name: String, root: Option<PathBuf>) -> PyResult<Self> {
        let mut core = Self {
            name,
            root: root.unwrap_or_else(|| PathBuf::from(".")),
            registry: rlab_core::Registry::new(),
            callables: BTreeMap::new(),
            component_schemas: BTreeMap::new(),
            component_requirements: BTreeMap::new(),
        };
        core.register_builtin(
            py,
            "filter",
            "rlab.text",
            "NativeTextFilter",
            py.get_type_bound::<PyNativeTextFilter>().unbind().into(),
        )?;
        core.register_builtin(
            py,
            "dedup",
            "rlab.simhash",
            "NativeSimhashDedup",
            py.get_type_bound::<PyNativeSimhashDedup>().unbind().into(),
        )?;
        core.register_builtin(
            py,
            "group",
            "rlab.documents",
            "NativeDocumentAssembler",
            py.get_type_bound::<PyNativeDocumentAssembler>().unbind().into(),
        )?;
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

    #[pyo3(signature = (kind, name, schema=None, requirements_json=None))]
    pub fn set_component_extras(
        &mut self,
        kind: &str,
        name: &str,
        schema: Option<Py<PyAny>>,
        requirements_json: Option<String>,
    ) {
        let key = registry_key(kind, name);
        if let Some(schema) = schema {
            self.component_schemas.insert(key.clone(), schema);
        }
        if let Some(requirements) = requirements_json {
            self.component_requirements.insert(key, requirements);
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
        self.component_schemas
            .get(&registry_key(kind, name))
            .map(|schema| schema.clone_ref(py))
    }

    pub fn requirements_json(&self, kind: &str, name: &str) -> Option<String> {
        self.component_requirements
            .get(&registry_key(kind, name))
            .cloned()
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
        let step = workflow_step(&record);

        if self.callables.contains_key(&key) {
            if kind == KIND_WORKFLOW {
                if let Some(step) = step {
                    self.append_workflow_step(py, &name, &step, &record, callable)?;
                    return Ok(());
                }
            }
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "duplicate declaration: {kind}:{name}"
            )));
        }

        if kind == KIND_WORKFLOW {
            if let Some(step) = step {
                self.register_first_workflow_step(py, &name, &step, record, callable)?;
                return Ok(());
            }
        }

        self.registry.insert(record).map_err(to_py_error)?;
        self.callables.insert(key, callable);
        Ok(())
    }

    fn register_builtin(
        &mut self,
        py: Python<'_>,
        kind: &str,
        name: &str,
        qualname: &str,
        callable: Py<PyAny>,
    ) -> PyResult<()> {
        let record = self.record(
            kind,
            name,
            "rlab._rlab",
            qualname,
            PathBuf::from("rlab/_rlab"),
            "Built-in rlab data primitive.",
            BTreeMap::from([
                (
                    "component_kind".to_string(),
                    Value::String(kind.to_string()),
                ),
                (
                    "reference".to_string(),
                    Value::String(format!("{kind}:{name}")),
                ),
                ("builtin".to_string(), Value::Bool(true)),
                (
                    "params_schema".to_string(),
                    builtin_params_schema(kind, name),
                ),
            ]),
            DEFAULT_VERSION,
            Some(vec![
                "rlab".to_string(),
                "builtin".to_string(),
                "data".to_string(),
            ]),
        )?;
        self.insert_record(py, record, callable)
    }

    fn register_first_workflow_step(
        &mut self,
        py: Python<'_>,
        workflow_name: &str,
        step: &str,
        mut record: rlab_core::RegistryRecord,
        callable: Py<PyAny>,
    ) -> PyResult<()> {
        let step_metadata = workflow_step_metadata(step, &record);
        record.metadata =
            BTreeMap::from([(KEY_STEPS.to_string(), Value::Array(vec![step_metadata]))]);
        self.registry.insert(record).map_err(to_py_error)?;
        self.callables.insert(
            registry_key(KIND_WORKFLOW, workflow_name),
            workflow_sentinel(py, workflow_name)?,
        );
        self.callables
            .insert(workflow_step_key(workflow_name, step), callable);
        Ok(())
    }

    fn append_workflow_step(
        &mut self,
        _py: Python<'_>,
        workflow_name: &str,
        step: &str,
        record: &rlab_core::RegistryRecord,
        callable: Py<PyAny>,
    ) -> PyResult<()> {
        let workflow_kind = rlab_core::RegistryKind::parse(KIND_WORKFLOW).map_err(to_py_error)?;
        let existing = self
            .registry
            .records
            .iter_mut()
            .find(|record| record.kind == workflow_kind && record.name == workflow_name)
            .ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err(format!(
                    "workflow record missing: {workflow_name}"
                ))
            })?;

        let steps = existing
            .metadata
            .entry(KEY_STEPS.to_string())
            .or_insert_with(|| Value::Array(Vec::new()));
        let Value::Array(steps) = steps else {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "workflow metadata steps must be an array: {workflow_name}"
            )));
        };
        if steps
            .iter()
            .any(|value| value.get(KEY_NAME).and_then(Value::as_str) == Some(step))
        {
            return Err(pyo3::exceptions::PyValueError::new_err(format!(
                "duplicate workflow step {workflow_name}:{step}"
            )));
        }
        steps.push(workflow_step_metadata(step, record));
        self.callables
            .insert(workflow_step_key(workflow_name, step), callable);
        Ok(())
    }
}

fn parse_metadata(metadata_json: &str) -> PyResult<BTreeMap<String, Value>> {
    from_json_str(metadata_json)
}

fn registry_key(kind: &str, name: &str) -> String {
    format!("{kind}:{name}")
}

fn builtin_params_schema(kind: &str, name: &str) -> Value {
    match (kind, name) {
        ("filter", "rlab.text") => serde_json::json!({
            "type": "object",
            "properties": {
                "rules": {
                    "type": "array",
                    "items": { "type": "object" },
                },
            },
            "additionalProperties": false,
        }),
        _ => serde_json::json!({
            "type": "object",
            "properties": {},
            "additionalProperties": false,
        }),
    }
}

fn workflow_step_key(workflow_name: &str, step: &str) -> String {
    registry_key(KIND_WORKFLOW_STEP, &format!("{workflow_name}:{step}"))
}

fn workflow_step(record: &rlab_core::RegistryRecord) -> Option<String> {
    record
        .metadata
        .get(KEY_STEP)
        .and_then(Value::as_str)
        .map(ToOwned::to_owned)
}

fn workflow_step_metadata(step: &str, record: &rlab_core::RegistryRecord) -> Value {
    let mut object = serde_json::Map::new();
    object.insert(KEY_NAME.to_string(), Value::String(step.to_string()));
    object.insert("schema_version".to_string(), Value::from(SCHEMA_VERSION));
    object.insert("module".to_string(), Value::String(record.module.clone()));
    object.insert(
        "qualname".to_string(),
        Value::String(record.qualname.clone()),
    );
    object.insert(
        "source".to_string(),
        Value::String(record.source.display().to_string()),
    );
    object.insert(
        KEY_METADATA.to_string(),
        Value::Object(record.metadata.clone().into_iter().collect()),
    );
    Value::Object(object)
}

fn relative_source(source: &Path, root: &Path) -> PathBuf {
    source
        .strip_prefix(root)
        .map(Path::to_path_buf)
        .unwrap_or_else(|_| source.to_path_buf())
}

fn workflow_sentinel(py: Python<'_>, name: &str) -> PyResult<Py<PyAny>> {
    let kwargs = PyDict::new_bound(py);
    kwargs.set_item("__rlab_workflow__", name)?;
    Ok(py
        .import_bound("types")?
        .getattr("SimpleNamespace")?
        .call((), Some(&kwargs))?
        .unbind())
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
