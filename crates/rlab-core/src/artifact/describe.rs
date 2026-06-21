use crate::config::ProjectPaths;
use crate::error::RlabResult;

use super::manifest::ArtifactManifest;
use super::store::ArtifactStore;

pub fn describe_artifact(
    paths: &ProjectPaths,
    kind: &str,
    name: &str,
    version_or_alias: &str,
) -> RlabResult<ArtifactManifest> {
    ArtifactStore::new(paths).describe_parts(kind, name, version_or_alias)
}

pub fn describe_artifact_reference(
    paths: &ProjectPaths,
    reference: &str,
) -> RlabResult<ArtifactManifest> {
    ArtifactStore::new(paths).describe(reference)
}
