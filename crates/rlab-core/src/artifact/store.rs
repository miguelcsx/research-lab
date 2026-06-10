use std::fs;
use std::path::PathBuf;

use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{ensure_dir, write_json_atomic, write_text_atomic};

use super::digest::sha256_file;
use super::index::append_index_row;
use super::manifest::{ArtifactManifest, ArtifactReference, ARTIFACT_SCHEMA_VERSION};
use super::promote::PromoteRequest;

#[derive(Debug, Clone)]
pub struct ArtifactStore {
    root: PathBuf,
}

impl ArtifactStore {
    pub fn new(paths: &ProjectPaths) -> Self {
        Self { root: paths.artifacts.clone() }
    }

    pub fn promote(&self, request: PromoteRequest) -> RlabResult<ArtifactManifest> {
        validate_promote_request(&request)?;
        ensure_dir(&self.root)?;
        let digest = sha256_file(&request.source)?;
        let prefix = digest_prefix(&digest)?;
        let rest = digest_rest(&digest)?;
        let object_dir = self.root.join("objects").join(prefix);
        ensure_dir(&object_dir)?;
        let object_path = object_dir.join(rest);
        if !object_path.exists() {
            fs::copy(&request.source, &object_path).map_err(|error| RlabError::io(&object_path, error))?;
        }
        let manifest = ArtifactManifest {
            schema_version: ARTIFACT_SCHEMA_VERSION,
            reference: ArtifactReference { kind: request.artifact_kind, name: request.name, version: request.version },
            sha256: digest,
            object_path: object_path.clone(),
            source_path: request.source,
            alias: request.alias,
            created_at: OffsetDateTime::now_utc(),
        };
        let manifest_path = self.root.join(&manifest.reference.kind).join(format!("{}@{}.json", manifest.reference.name, manifest.reference.version));
        if let Some(parent) = manifest_path.parent() {
            ensure_dir(parent)?;
        }
        write_json_atomic(&manifest_path, &manifest)?;
        append_index_row(&self.root.join("index.jsonl"), &manifest)?;
        if let Some(alias) = &manifest.alias {
            let alias_path = self.root.join(&manifest.reference.kind).join(&manifest.reference.name).join(alias);
            if let Some(parent) = alias_path.parent() {
                ensure_dir(parent)?;
            }
            write_text_atomic(&alias_path, &manifest.reference.version)?;
        }
        Ok(manifest)
    }
}

fn validate_promote_request(request: &PromoteRequest) -> RlabResult<()> {
    if request.artifact_kind.trim().is_empty() || request.name.trim().is_empty() || request.version.trim().is_empty() {
        return Err(RlabError::Artifact { message: "artifact kind, name, and version are required".to_string() });
    }
    if !request.source.is_file() {
        return Err(RlabError::Artifact { message: format!("artifact source is not a file: {}", request.source.display()) });
    }
    Ok(())
}

fn digest_prefix(digest: &str) -> RlabResult<&str> {
    match digest.get(0..2) {
        Some(value) => Ok(value),
        None => Err(RlabError::Artifact { message: "invalid digest prefix".to_string() }),
    }
}

fn digest_rest(digest: &str) -> RlabResult<&str> {
    match digest.get(2..) {
        Some(value) if !value.is_empty() => Ok(value),
        _ => Err(RlabError::Artifact { message: "invalid digest body".to_string() }),
    }
}
