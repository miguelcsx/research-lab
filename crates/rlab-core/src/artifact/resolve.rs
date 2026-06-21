use std::path::PathBuf;

use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::run::{list_runs, RunStatus};

use super::store::ArtifactStore;

pub fn resolve_path_reference(paths: &ProjectPaths, value: &str) -> RlabResult<PathBuf> {
    if value.starts_with("artifact:") {
        return ArtifactStore::new(paths).resolve_path(value);
    }
    if value.starts_with('@') {
        return resolve_run_reference(paths, value);
    }
    let path = PathBuf::from(value);
    if path.is_absolute() {
        Ok(path)
    } else {
        Ok(paths.root.join(path))
    }
}

pub fn resolve_param_refs(paths: &ProjectPaths, params: Value) -> RlabResult<Value> {
    let Value::Object(map) = params else {
        return Ok(params);
    };
    let mut resolved = serde_json::Map::with_capacity(map.len());
    for (key, value) in map {
        let value = match &value {
            Value::String(text) if text.starts_with('@') => Value::String(
                resolve_run_reference(paths, text)?
                    .to_string_lossy()
                    .into_owned(),
            ),
            _ => value,
        };
        resolved.insert(key, value);
    }
    Ok(Value::Object(resolved))
}

pub fn resolve_run_reference(paths: &ProjectPaths, reference: &str) -> RlabResult<PathBuf> {
    let (target, suffix) = match reference[1..].split_once('/') {
        Some((target, suffix)) => (target, Some(suffix)),
        None => (&reference[1..], None),
    };
    let (kind, name) = target
        .split_once(':')
        .ok_or_else(|| RlabError::Validation {
            message: format!(
                "invalid run reference '{reference}': expected @<kind>:<name>[/suffix]"
            ),
        })?;
    let latest = list_runs(paths)?
        .into_iter()
        .filter(|run| {
            run.operation == kind && run.name == name && run.status == RunStatus::Completed
        })
        .max_by(|left, right| left.id.cmp(&right.id))
        .ok_or_else(|| RlabError::Validation {
            message: format!("no completed run for '{kind}:{name}' referenced by '{reference}'"),
        })?;
    let mut path = PathBuf::from(latest.path);
    if let Some(suffix) = suffix {
        path.push(suffix);
    }
    Ok(path)
}
