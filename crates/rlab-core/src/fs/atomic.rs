use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};

use serde::Serialize;

use crate::error::{RlabError, RlabResult};

pub fn write_text_atomic(path: &Path, content: &str) -> RlabResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| RlabError::io(parent, error))?;
    }
    let tmp_path = temporary_path(path)?;
    fs::write(&tmp_path, content).map_err(|error| RlabError::io(&tmp_path, error))?;
    fs::rename(&tmp_path, path).map_err(|error| RlabError::io(path, error))
}

pub fn write_json_atomic<T: Serialize>(path: &Path, value: &T) -> RlabResult<()> {
    let content = serde_json::to_string_pretty(value).map_err(RlabError::serialization)?;
    write_text_atomic(path, &content)
}

pub fn write_yaml_atomic<T: Serialize>(path: &Path, value: &T) -> RlabResult<()> {
    let content = serde_yaml::to_string(value).map_err(RlabError::serialization)?;
    write_text_atomic(path, &content)
}

pub fn append_line(path: &Path, line: &str) -> RlabResult<()> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|error| RlabError::io(parent, error))?;
    }
    let mut file = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .map_err(|error| RlabError::io(path, error))?;
    file.write_all(line.as_bytes())
        .map_err(|error| RlabError::io(path, error))?;
    file.write_all(b"\n")
        .map_err(|error| RlabError::io(path, error))
}

fn temporary_path(path: &Path) -> RlabResult<PathBuf> {
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| RlabError::Validation {
            message: format!("path has no valid file name: {}", path.display()),
        })?;
    let process_id = std::process::id();
    let nanos = time::OffsetDateTime::now_utc().unix_timestamp_nanos();
    Ok(path.with_file_name(format!(".{file_name}.{process_id}.{nanos}.tmp")))
}
