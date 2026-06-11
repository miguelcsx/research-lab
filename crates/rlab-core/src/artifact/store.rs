use std::fs;
use std::path::{Path, PathBuf};

use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{ensure_dir, write_json_atomic, write_text_atomic};

use super::digest::sha256_file;
use super::index::append_index_row;
use super::manifest::{ArtifactManifest, ArtifactReference, ARTIFACT_SCHEMA_VERSION};
use super::promote::PromoteRequest;

const OBJECTS_DIR: &str = "objects";
const INDEX_FILE: &str = "index.jsonl";
const MANIFEST_EXTENSION: &str = "json";
const DIGEST_PREFIX_BYTES: usize = 2;

const REQUIRED_FIELDS_ERROR: &str = "artifact kind, name, and version are required";
const INVALID_DIGEST_PREFIX_ERROR: &str = "invalid digest prefix";
const INVALID_DIGEST_BODY_ERROR: &str = "invalid digest body";

#[derive(Debug, Clone)]
pub struct ArtifactStore {
    root: PathBuf,
}

impl ArtifactStore {
    pub fn new(paths: &ProjectPaths) -> Self {
        Self {
            root: paths.artifacts.clone(),
        }
    }

    pub fn promote(&self, request: PromoteRequest) -> RlabResult<ArtifactManifest> {
        validate_promote_request(&request)?;
        ensure_dir(&self.root)?;

        let digest = sha256_file(&request.source)?;
        let object_path = self.promote_object(&request.source, &digest)?;
        let manifest = manifest_from_request(request, digest, object_path);

        self.write_manifest(&manifest)?;
        self.append_index(&manifest)?;
        self.write_alias(&manifest)?;

        Ok(manifest)
    }

    fn promote_object(&self, source: &Path, digest: &str) -> RlabResult<PathBuf> {
        let object_path = self.object_path(digest)?;

        if object_path.exists() {
            return Ok(object_path);
        }

        ensure_parent_dir(&object_path)?;
        copy_file(source, &object_path)?;

        Ok(object_path)
    }

    fn object_path(&self, digest: &str) -> RlabResult<PathBuf> {
        let digest = DigestParts::parse(digest)?;

        Ok(self
            .root
            .join(OBJECTS_DIR)
            .join(digest.prefix)
            .join(digest.body))
    }

    fn write_manifest(&self, manifest: &ArtifactManifest) -> RlabResult<()> {
        let path = self.manifest_path(&manifest.reference);
        ensure_parent_dir(&path)?;
        write_json_atomic(&path, manifest)
    }

    fn manifest_path(&self, reference: &ArtifactReference) -> PathBuf {
        self.root
            .join(&reference.kind)
            .join(manifest_file_name(reference))
    }

    fn append_index(&self, manifest: &ArtifactManifest) -> RlabResult<()> {
        append_index_row(&self.root.join(INDEX_FILE), manifest)
    }

    fn write_alias(&self, manifest: &ArtifactManifest) -> RlabResult<()> {
        let Some(alias) = manifest.alias.as_ref() else {
            return Ok(());
        };

        let path = self.alias_path(&manifest.reference, alias);
        ensure_parent_dir(&path)?;
        write_text_atomic(&path, &manifest.reference.version)
    }

    fn alias_path(&self, reference: &ArtifactReference, alias: &str) -> PathBuf {
        self.root
            .join(&reference.kind)
            .join(&reference.name)
            .join(alias)
    }
}

struct DigestParts<'a> {
    prefix: &'a str,
    body: &'a str,
}

impl<'a> DigestParts<'a> {
    fn parse(digest: &'a str) -> RlabResult<Self> {
        let prefix = digest_prefix(digest)?;
        let body = digest_body(digest)?;

        Ok(Self { prefix, body })
    }
}

fn manifest_from_request(
    request: PromoteRequest,
    digest: String,
    object_path: PathBuf,
) -> ArtifactManifest {
    ArtifactManifest {
        schema_version: ARTIFACT_SCHEMA_VERSION,
        reference: ArtifactReference {
            kind: request.artifact_kind,
            name: request.name,
            version: request.version,
        },
        sha256: digest,
        object_path,
        source_path: request.source,
        alias: request.alias,
        created_at: OffsetDateTime::now_utc(),
    }
}

fn manifest_file_name(reference: &ArtifactReference) -> String {
    format!(
        "{}@{}.{}",
        reference.name, reference.version, MANIFEST_EXTENSION
    )
}

fn validate_promote_request(request: &PromoteRequest) -> RlabResult<()> {
    validate_required_artifact_fields(request)?;
    validate_source_file(&request.source)
}

fn validate_required_artifact_fields(request: &PromoteRequest) -> RlabResult<()> {
    if is_blank(&request.artifact_kind) || is_blank(&request.name) || is_blank(&request.version) {
        return Err(artifact_error(REQUIRED_FIELDS_ERROR));
    }

    Ok(())
}

fn validate_source_file(source: &Path) -> RlabResult<()> {
    if source.is_file() {
        return Ok(());
    }

    Err(artifact_error(format!(
        "artifact source is not a file: {}",
        source.display()
    )))
}

fn digest_prefix(digest: &str) -> RlabResult<&str> {
    match digest.get(..DIGEST_PREFIX_BYTES) {
        Some(value) if !value.is_empty() => Ok(value),
        _ => Err(artifact_error(INVALID_DIGEST_PREFIX_ERROR)),
    }
}

fn digest_body(digest: &str) -> RlabResult<&str> {
    match digest.get(DIGEST_PREFIX_BYTES..) {
        Some(value) if !value.is_empty() => Ok(value),
        _ => Err(artifact_error(INVALID_DIGEST_BODY_ERROR)),
    }
}

fn ensure_parent_dir(path: &Path) -> RlabResult<()> {
    match path.parent() {
        Some(parent) => ensure_dir(parent),
        None => Ok(()),
    }
}

fn copy_file(source: &Path, destination: &Path) -> RlabResult<u64> {
    fs::copy(source, destination).map_err(|error| RlabError::io(destination, error))
}

fn is_blank(value: &str) -> bool {
    value.trim().is_empty()
}

fn artifact_error(message: impl Into<String>) -> RlabError {
    RlabError::Artifact {
        message: message.into(),
    }
}
