use std::fs;
use std::path::Path;

use serde::de::DeserializeOwned;

use crate::error::{RlabError, RlabResult};

pub fn read_optional_toml<T>(path: &Path) -> RlabResult<Option<T>>
where
    T: DeserializeOwned,
{
    if !path.exists() {
        return Ok(None);
    }

    read_toml(path).map(Some)
}

fn read_toml<T>(path: &Path) -> RlabResult<T>
where
    T: DeserializeOwned,
{
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    toml::from_str(&content).map_err(RlabError::serialization)
}
