use std::fs;
use std::path::Path;

use serde::{de::DeserializeOwned, Serialize};

use crate::error::{RlabError, RlabResult};
use crate::fs::append_line;

pub fn append_jsonl<T: Serialize>(path: &Path, value: &T) -> RlabResult<()> {
    let line = serde_json::to_string(value).map_err(RlabError::serialization)?;
    append_line(path, &line)
}

pub fn read_jsonl<T: DeserializeOwned>(path: &Path) -> RlabResult<Vec<T>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    content
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str::<T>(line).map_err(RlabError::serialization))
        .collect()
}
