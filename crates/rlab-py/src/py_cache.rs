use std::fs;
use std::io::{BufRead, BufReader, Write};
use std::path::PathBuf;

use pyo3::prelude::*;
use pyo3::types::PyList;
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::convert::json::{from_json_str, to_json};
use crate::error::to_py_error;

#[pyclass(name = "CacheEntry")]
#[derive(Clone)]
pub struct PyCacheEntry {
    entry: rlab_core::CacheEntry,
}

#[pymethods]
impl PyCacheEntry {
    #[getter]
    pub fn path(&self, py: Python<'_>) -> PyResult<PyObject> {
        py_path(py, PathBuf::from(&self.entry.path))
    }

    #[getter]
    pub fn size_bytes(&self) -> u64 {
        self.entry.bytes
    }

    #[getter]
    pub fn bytes(&self) -> u64 {
        self.entry.bytes
    }

    #[getter]
    pub fn kind(&self) -> String {
        self.entry.kind.clone()
    }
}

impl From<rlab_core::CacheEntry> for PyCacheEntry {
    fn from(entry: rlab_core::CacheEntry) -> Self {
        Self { entry }
    }
}

#[pyfunction(name = "cache_path")]
#[pyo3(signature = (root=None))]
pub fn cache_path_py(py: Python<'_>, root: Option<PathBuf>) -> PyResult<PyObject> {
    py_path(py, project_paths(root).cache)
}

#[pyfunction(name = "list_cache")]
#[pyo3(signature = (root=None))]
pub fn list_cache_py(root: Option<PathBuf>) -> PyResult<Vec<PyCacheEntry>> {
    rlab_core::cache_list(&project_paths(root))
        .map(|entries| entries.into_iter().map(PyCacheEntry::from).collect())
        .map_err(to_py_error)
}

#[pyfunction(name = "cache_size")]
pub fn cache_size_py(entries: Vec<PyRef<'_, PyCacheEntry>>) -> u64 {
    entries.iter().map(|entry| entry.entry.bytes).sum()
}

#[pyfunction(name = "cache_key")]
pub fn cache_key_py(py: Python<'_>, value: PyObject) -> PyResult<String> {
    let value = py_to_json(py, value)?;
    let payload = serde_json::to_string(&value)
        .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
    let mut hasher = Sha256::new();
    hasher.update(payload.as_bytes());
    let digest = hasher.finalize();
    Ok(format!("{digest:x}").chars().take(16).collect())
}

#[pyfunction(name = "runtime_cache_path")]
#[pyo3(signature = (ctx, *parts))]
pub fn runtime_cache_path_py(
    py: Python<'_>,
    ctx: PyObject,
    parts: Vec<String>,
) -> PyResult<PyObject> {
    let ctx = ctx.bind(py);
    let cache_dir = ctx.getattr("cache_dir")?;
    let root = if cache_dir.is_none() {
        let project_root = ctx.getattr("project_root")?.extract::<PathBuf>()?;
        project_root.join(".rlab/cache")
    } else {
        cache_dir.extract::<PathBuf>()?
    };
    let mut path = root;
    for part in parts {
        path.push(part);
    }
    if path.extension().is_some() {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).map_err(|error| {
                pyo3::exceptions::PyOSError::new_err(format!(
                    "failed to create cache parent {}: {error}",
                    parent.display()
                ))
            })?;
        }
    } else {
        fs::create_dir_all(&path).map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to create cache directory {}: {error}",
                path.display()
            ))
        })?;
    }
    py_path(py, path)
}

#[pyfunction(name = "read_jsonl")]
pub fn read_jsonl_py(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    let file = fs::File::open(&path).map_err(|error| {
        pyo3::exceptions::PyOSError::new_err(format!(
            "failed to open JSONL cache {}: {error}",
            path.display()
        ))
    })?;
    let rows = PyList::empty_bound(py);
    for (index, line) in BufReader::new(file).lines().enumerate() {
        let line = line.map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to read JSONL cache {}: {error}",
                path.display()
            ))
        })?;
        if line.trim().is_empty() {
            continue;
        }
        let value: Value = serde_json::from_str(&line).map_err(|error| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "invalid JSONL row {} in {}: {error}",
                index + 1,
                path.display()
            ))
        })?;
        if !value.is_object() {
            return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                "JSONL row must be an object: {}",
                path.display()
            )));
        }
        rows.append(py_from_json(py, &value)?)?;
    }
    Ok(rows.unbind().into())
}

#[pyfunction(name = "write_jsonl_atomic")]
pub fn write_jsonl_atomic_py(py: Python<'_>, path: PathBuf, rows: PyObject) -> PyResult<()> {
    write_jsonl_rows(
        py,
        path,
        rows.bind(py).iter()?.map(|item| item.map(Bound::unbind)),
    )
}

#[pyfunction(name = "write_through_jsonl_atomic")]
pub fn write_through_jsonl_atomic_py(
    py: Python<'_>,
    path: PathBuf,
    rows: PyObject,
    encode: PyObject,
) -> PyResult<PyObject> {
    let mut passthrough = Vec::new();
    let mut encoded = Vec::new();
    for item in rows.bind(py).iter()? {
        let row = item?.unbind();
        let encoded_row = encode.bind(py).call1((row.clone_ref(py),))?.unbind();
        passthrough.push(row);
        encoded.push(encoded_row);
    }
    write_jsonl_rows(py, path, encoded.into_iter().map(Ok))?;
    Ok(PyList::new_bound(py, passthrough).unbind().into())
}

fn project_paths(root: Option<PathBuf>) -> rlab_core::ProjectPaths {
    let root = root.unwrap_or_else(|| PathBuf::from("."));
    rlab_core::ProjectPaths {
        root: root.clone(),
        runs: root.join(".rlab/runs"),
        artifacts: root.join(".rlab/artifacts"),
        cache: root.join(".rlab/cache"),
        registry_cache: root.join(".rlab/cache/registry.json"),
    }
}

fn write_jsonl_rows<I>(py: Python<'_>, path: PathBuf, rows: I) -> PyResult<()>
where
    I: IntoIterator<Item = PyResult<PyObject>>,
{
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to create JSONL parent {}: {error}",
                parent.display()
            ))
        })?;
    }
    let temporary = path.with_extension(format!(
        "{}tmp",
        path.extension()
            .and_then(|value| value.to_str())
            .map(|value| format!("{value}."))
            .unwrap_or_default()
    ));
    {
        let mut file = fs::File::create(&temporary).map_err(|error| {
            pyo3::exceptions::PyOSError::new_err(format!(
                "failed to create JSONL temp {}: {error}",
                temporary.display()
            ))
        })?;
        for row in rows {
            let value = py_to_json(py, row?)?;
            if !value.is_object() {
                return Err(pyo3::exceptions::PyTypeError::new_err(format!(
                    "JSONL row must be an object: {}",
                    path.display()
                )));
            }
            let line = serde_json::to_string(&value)
                .map_err(|error| pyo3::exceptions::PyValueError::new_err(error.to_string()))?;
            writeln!(file, "{line}").map_err(|error| {
                pyo3::exceptions::PyOSError::new_err(format!(
                    "failed to write JSONL temp {}: {error}",
                    temporary.display()
                ))
            })?;
        }
    }
    fs::rename(&temporary, &path).map_err(|error| {
        pyo3::exceptions::PyOSError::new_err(format!(
            "failed to replace JSONL cache {}: {error}",
            path.display()
        ))
    })
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

fn py_from_json(py: Python<'_>, value: &Value) -> PyResult<PyObject> {
    Ok(py
        .import_bound("json")?
        .call_method1("loads", (to_json(value)?,))?
        .unbind())
}

fn py_path(py: Python<'_>, path: PathBuf) -> PyResult<PyObject> {
    Ok(py
        .import_bound("pathlib")?
        .getattr("Path")?
        .call1((path.to_string_lossy().to_string(),))?
        .unbind())
}
