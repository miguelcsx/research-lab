use std::fs;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::manifest::{parse_artifact_reference, ArtifactManifest};

pub fn describe_artifact(
    paths: &ProjectPaths,
    kind: &str,
    name: &str,
    version_or_alias: &str,
) -> RlabResult<ArtifactManifest> {
    let version = resolve_version(paths, kind, name, version_or_alias)?;
    let path = paths
        .artifacts
        .join(kind)
        .join(format!("{name}@{version}.json"));
    let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
    serde_json::from_str(&content).map_err(RlabError::serialization)
}

pub fn describe_artifact_reference(
    paths: &ProjectPaths,
    reference: &str,
) -> RlabResult<ArtifactManifest> {
    let reference = parse_artifact_reference(reference)?;
    describe_artifact(paths, &reference.kind, &reference.name, &reference.version)
}

fn resolve_version(
    paths: &ProjectPaths,
    kind: &str,
    name: &str,
    version_or_alias: &str,
) -> RlabResult<String> {
    let manifest = paths
        .artifacts
        .join(kind)
        .join(format!("{name}@{version_or_alias}.json"));
    if manifest.is_file() {
        return Ok(version_or_alias.to_string());
    }

    let alias = paths.artifacts.join(kind).join(name).join(version_or_alias);
    match fs::read_to_string(&alias) {
        Ok(version) => {
            let trimmed = version.trim();
            if trimmed.is_empty() {
                return Err(RlabError::Artifact {
                    message: format!("artifact alias is empty: {}", alias.display()),
                });
            }
            Ok(trimmed.to_string())
        }
        Err(error) => Err(RlabError::io(&alias, error)),
    }
}
