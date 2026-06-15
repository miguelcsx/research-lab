use std::fs;
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH};

use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

use crate::convert::json::{from_json_str, to_pretty_json};

#[pyclass(name = "RetentionPolicy")]
#[derive(Clone)]
pub struct PyRetentionPolicy {
    keep_last: Option<usize>,
    keep_milestones: bool,
}

#[pymethods]
impl PyRetentionPolicy {
    #[new]
    #[pyo3(signature = (keep_last=None, keep_milestones=true))]
    pub fn new(keep_last: Option<usize>, keep_milestones: bool) -> PyResult<Self> {
        if matches!(keep_last, Some(0)) {
            return Err(pyo3::exceptions::PyValueError::new_err(
                "keep_last must be positive",
            ));
        }
        Ok(Self {
            keep_last,
            keep_milestones,
        })
    }
}

impl Default for PyRetentionPolicy {
    fn default() -> Self {
        Self {
            keep_last: None,
            keep_milestones: true,
        }
    }
}

#[pyclass(name = "CheckpointRecord")]
#[derive(Clone, Serialize, Deserialize)]
pub struct PyCheckpointRecord {
    name: String,
    path: PathBuf,
    step: i64,
    metric: Option<f64>,
    milestone: bool,
}

#[pymethods]
impl PyCheckpointRecord {
    #[getter]
    pub fn name(&self) -> String {
        self.name.clone()
    }

    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, &self.path)
    }

    #[getter]
    pub fn step(&self) -> i64 {
        self.step
    }

    #[getter]
    pub fn metric(&self) -> Option<f64> {
        self.metric
    }

    #[getter]
    pub fn milestone(&self) -> bool {
        self.milestone
    }
}

#[derive(Serialize, Deserialize)]
struct CheckpointManifest {
    schema_version: u32,
    name: String,
    step: i64,
    metric: Option<f64>,
    milestone: bool,
}

#[pyclass(name = "CheckpointManager")]
pub struct PyCheckpointManager {
    root: PathBuf,
    serializer: PyObject,
    retention: PyRetentionPolicy,
}

#[pymethods]
impl PyCheckpointManager {
    #[new]
    #[pyo3(signature = (root, serializer, retention=None))]
    pub fn new(
        root: PathBuf,
        serializer: PyObject,
        retention: Option<PyRetentionPolicy>,
    ) -> PyResult<Self> {
        fs::create_dir_all(&root)?;
        Ok(Self {
            root,
            serializer,
            retention: retention.unwrap_or_default(),
        })
    }

    #[pyo3(signature = (name, state, step, metric=None, milestone=false))]
    pub fn save(
        &self,
        py: Python<'_>,
        name: &str,
        state: PyObject,
        step: i64,
        metric: Option<f64>,
        milestone: bool,
    ) -> PyResult<PyCheckpointRecord> {
        validate_name(name)?;
        let target = self.root.join(name);
        if target.exists() {
            return Err(pyo3::exceptions::PyFileExistsError::new_err(format!(
                "checkpoint already exists: {}",
                target.display()
            )));
        }

        let temporary = self.root.join(unique_hidden_path(name));
        let _ = fs::remove_dir_all(&temporary);
        fs::create_dir_all(&temporary)?;
        let result = (|| -> PyResult<()> {
            self.serializer
                .bind(py)
                .call_method1("write", (py_path(py, &temporary)?, state))?;
            write_manifest(
                &temporary.join("checkpoint.json"),
                &CheckpointManifest {
                    schema_version: 1,
                    name: name.to_string(),
                    step,
                    metric,
                    milestone,
                },
            )?;
            self.serializer
                .bind(py)
                .call_method1("validate", (py_path(py, &temporary)?,))?;
            fs::rename(&temporary, &target)?;
            Ok(())
        })();

        if result.is_err() {
            let _ = fs::remove_dir_all(&temporary);
        }
        result?;

        let record = PyCheckpointRecord {
            name: name.to_string(),
            path: target,
            step,
            metric,
            milestone,
        };
        self.alias("latest", &record.path)?;
        let records = self.records()?;
        if metric.is_some() && self.is_best(&record, &records) {
            self.alias("best", &record.path)?;
        }
        self.prune_records(&records)?;
        Ok(record)
    }

    #[pyo3(signature = (reference=None))]
    pub fn load(&self, py: Python<'_>, reference: Option<PyObject>) -> PyResult<PyObject> {
        let path = match reference {
            Some(reference) => self.resolve_load_reference(py, reference)?,
            None => resolve_reference(&self.root, "latest"),
        };
        self.serializer
            .bind(py)
            .call_method1("validate", (py_path(py, &path)?,))?;
        Ok(self
            .serializer
            .bind(py)
            .call_method1("read", (py_path(py, &path)?,))?
            .unbind())
    }

    pub fn records(&self) -> PyResult<Vec<PyCheckpointRecord>> {
        let mut records = Vec::new();
        for entry in fs::read_dir(&self.root)? {
            let path = entry?.path();
            let manifest = path.join("checkpoint.json");
            if path.is_symlink() || !manifest.is_file() {
                continue;
            }
            let manifest = read_manifest(&manifest)?;
            records.push(PyCheckpointRecord {
                name: manifest.name,
                path,
                step: manifest.step,
                metric: manifest.metric,
                milestone: manifest.milestone,
            });
        }
        records.sort_by_key(|record| record.step);
        Ok(records)
    }

    pub fn prune(&self) -> PyResult<()> {
        let records = self.records()?;
        self.prune_records(&records)
    }
}

impl PyCheckpointManager {
    fn resolve_load_reference(&self, py: Python<'_>, reference: PyObject) -> PyResult<PathBuf> {
        let path = reference.extract::<PathBuf>(py)?;
        if path.is_absolute() || path.join("checkpoint.json").is_file() {
            return Ok(path);
        }
        Ok(resolve_reference(&self.root, &path.to_string_lossy()))
    }

    fn is_best(&self, candidate: &PyCheckpointRecord, records: &[PyCheckpointRecord]) -> bool {
        let best = self.root.join("best");
        let Ok(best_path) = best.canonicalize() else {
            return true;
        };
        records
            .iter()
            .find(|record| record.path.canonicalize().ok() == Some(best_path.clone()))
            .is_none_or(|record| {
                record
                    .metric
                    .is_none_or(|value| candidate.metric.is_some_and(|metric| metric < value))
            })
    }

    fn prune_records(&self, records: &[PyCheckpointRecord]) -> PyResult<()> {
        let mut keep = Vec::new();
        for alias in ["latest", "best"] {
            if let Ok(path) = self.root.join(alias).canonicalize() {
                keep.push(path);
            }
        }
        if let Some(count) = self.retention.keep_last {
            keep.extend(
                records
                    .iter()
                    .rev()
                    .take(count)
                    .filter_map(|record| record.path.canonicalize().ok()),
            );
        } else {
            keep.extend(
                records
                    .iter()
                    .filter_map(|record| record.path.canonicalize().ok()),
            );
        }
        if self.retention.keep_milestones {
            keep.extend(
                records
                    .iter()
                    .filter(|record| record.milestone)
                    .filter_map(|record| record.path.canonicalize().ok()),
            );
        }
        for record in records {
            if let Ok(path) = record.path.canonicalize() {
                if !keep.contains(&path) {
                    fs::remove_dir_all(&record.path)?;
                }
            }
        }
        Ok(())
    }

    fn alias(&self, name: &str, target: &Path) -> PyResult<()> {
        let alias = self.root.join(name);
        let temporary = self.root.join(unique_hidden_path(name));
        let _ = fs::remove_file(&temporary);
        #[cfg(unix)]
        std::os::unix::fs::symlink(
            target.file_name().ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("checkpoint path has no file name")
            })?,
            &temporary,
        )?;
        #[cfg(not(unix))]
        std::os::windows::fs::symlink_dir(
            target.file_name().ok_or_else(|| {
                pyo3::exceptions::PyValueError::new_err("checkpoint path has no file name")
            })?,
            &temporary,
        )?;
        fs::rename(temporary, alias)?;
        Ok(())
    }
}

fn validate_name(name: &str) -> PyResult<()> {
    if name.is_empty() || name.contains('/') || name.contains('\\') {
        return Err(pyo3::exceptions::PyValueError::new_err(format!(
            "invalid checkpoint name: {name:?}"
        )));
    }
    Ok(())
}

fn unique_hidden_path(name: &str) -> String {
    format!(".{name}.{}.{}", std::process::id(), unique_nanos())
}

fn unique_nanos() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_nanos())
        .unwrap_or_default()
}

fn resolve_reference(root: &Path, reference: &str) -> PathBuf {
    let path = PathBuf::from(reference);
    if path.is_absolute() {
        path
    } else {
        root.join(path)
    }
}

fn write_manifest(path: &Path, manifest: &CheckpointManifest) -> PyResult<()> {
    fs::write(path, format!("{}\n", to_pretty_json(manifest)?))?;
    Ok(())
}

fn read_manifest(path: &Path) -> PyResult<CheckpointManifest> {
    from_json_str(&fs::read_to_string(path)?)
}

fn py_path(py: Python<'_>, path: &Path) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}
