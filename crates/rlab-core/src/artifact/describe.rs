use std::fs;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::manifest::ArtifactManifest;

pub fn describe_artifact(paths: &ProjectPaths, kind: &str, name: &str, version: &str) -> RlabResult<ArtifactManifest> {
    let path = paths.artifacts.join(kind).join(format!("{name}@{version}.json"));
    let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
    serde_json::from_str(&content).map_err(RlabError::serialization)
}
