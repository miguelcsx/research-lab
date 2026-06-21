use std::fs;
use std::path::{Path, PathBuf};

use serde::Serialize;
use time::OffsetDateTime;
use walkdir::WalkDir;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{ensure_child_path, ensure_dir, write_json_atomic, write_text_atomic};

use super::digest::{sha256_bytes, sha256_file};
use super::index::append_index_row;
use super::manifest::{
    parse_artifact_path_reference, ArtifactManifest, ArtifactReference, ArtifactStorageType,
    TreeEntry, TreeManifest, ARTIFACT_SCHEMA_VERSION, TREE_SCHEMA_VERSION,
};
use super::promote::PromoteRequest;

const OBJECTS_DIR: &str = "objects";
const BLOBS_DIR: &str = "blobs";
const TREES_DIR: &str = "trees";
const MATERIALIZED_DIR: &str = "materialized";
const INDEX_FILE: &str = "index.jsonl";
const MANIFEST_EXTENSION: &str = "json";
const DIGEST_PREFIX_BYTES: usize = 2;

#[derive(Debug, Clone)]
pub struct ArtifactStore {
    root: PathBuf,
}

#[derive(Debug, Clone, Serialize)]
pub struct StoredArtifact {
    pub sha256: String,
    pub storage_type: ArtifactStorageType,
    pub object_path: PathBuf,
    pub source_path: PathBuf,
    pub size_bytes: u64,
}

impl ArtifactStore {
    pub fn new(paths: &ProjectPaths) -> Self {
        Self {
            root: paths.artifacts.clone(),
        }
    }

    pub fn promote(&self, request: PromoteRequest) -> RlabResult<ArtifactManifest> {
        validate_required_artifact_fields(&request)?;
        let stored = self.ingest_path(&request.source)?;
        let version = if request.version.trim().is_empty() {
            stored.sha256.clone()
        } else {
            request.version
        };
        let manifest = ArtifactManifest {
            schema_version: ARTIFACT_SCHEMA_VERSION,
            reference: ArtifactReference {
                kind: request.artifact_kind,
                name: request.name,
                version,
            },
            sha256: stored.sha256,
            storage_type: stored.storage_type,
            object_path: stored.object_path,
            source_path: stored.source_path,
            size_bytes: stored.size_bytes,
            alias: request.alias,
            created_at: OffsetDateTime::now_utc(),
        };
        self.write_manifest(&manifest)?;
        self.append_index(&manifest)?;
        self.write_alias(&manifest)?;
        Ok(manifest)
    }

    pub fn ingest_path(&self, source: &Path) -> RlabResult<StoredArtifact> {
        ensure_dir(&self.root)?;
        if source.is_file() {
            self.ingest_file(source)
        } else if source.is_dir() {
            self.ingest_directory(source)
        } else {
            Err(artifact_error(format!(
                "artifact source is not a file or directory: {}",
                source.display()
            )))
        }
    }

    pub fn describe(&self, reference: &str) -> RlabResult<ArtifactManifest> {
        let parsed = parse_artifact_path_reference(reference)?;
        self.describe_parts(
            &parsed.reference.kind,
            &parsed.reference.name,
            &parsed.reference.version,
        )
    }

    pub fn describe_parts(
        &self,
        kind: &str,
        name: &str,
        version_or_alias: &str,
    ) -> RlabResult<ArtifactManifest> {
        let version = self.resolve_version(kind, name, version_or_alias)?;
        let path = self
            .root
            .join(kind)
            .join(manifest_file_name(name, &version));
        let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
        serde_json::from_str(&content).map_err(RlabError::serialization)
    }

    pub fn resolve_path(&self, reference: &str) -> RlabResult<PathBuf> {
        let parsed = parse_artifact_path_reference(reference)?;
        let manifest = self.describe_parts(
            &parsed.reference.kind,
            &parsed.reference.name,
            &parsed.reference.version,
        )?;
        let base = match manifest.storage_type {
            ArtifactStorageType::File => manifest.object_path.clone(),
            ArtifactStorageType::Directory => self.materialize_tree(&manifest)?,
        };
        match parsed.suffix {
            Some(suffix) => ensure_child_path(&base, &suffix),
            None => Ok(base),
        }
    }

    pub fn export(&self, reference: &str, target: &Path) -> RlabResult<PathBuf> {
        let source = self.resolve_path(reference)?;
        if target.exists() {
            return Err(artifact_error(format!(
                "export target already exists: {}",
                target.display()
            )));
        }
        if source.is_dir() {
            copy_dir_recursive(&source, target)?;
        } else {
            ensure_parent_dir(target)?;
            copy_file_fast(&source, target)?;
        }
        Ok(target.to_path_buf())
    }

    pub fn list(
        &self,
        kind: Option<&str>,
        name: Option<&str>,
        alias: Option<&str>,
    ) -> RlabResult<Vec<ArtifactManifest>> {
        let index = self.root.join(INDEX_FILE);
        if !index.exists() {
            return Ok(Vec::new());
        }
        let content = fs::read_to_string(&index).map_err(|error| RlabError::io(&index, error))?;
        let mut rows = Vec::new();
        for line in content.lines().filter(|line| !line.trim().is_empty()) {
            let manifest: ArtifactManifest =
                serde_json::from_str(line).map_err(RlabError::serialization)?;
            if kind.is_some_and(|value| value != manifest.reference.kind) {
                continue;
            }
            if name.is_some_and(|value| value != manifest.reference.name) {
                continue;
            }
            if alias.is_some_and(|value| manifest.alias.as_deref() != Some(value)) {
                continue;
            }
            rows.push(manifest);
        }
        rows.sort_by(|left, right| {
            left.reference
                .kind
                .cmp(&right.reference.kind)
                .then(left.reference.name.cmp(&right.reference.name))
                .then(left.reference.version.cmp(&right.reference.version))
        });
        Ok(rows)
    }

    pub fn materialized_root(&self) -> PathBuf {
        self.root.join(MATERIALIZED_DIR)
    }

    pub fn object_root(&self) -> PathBuf {
        self.root.join(OBJECTS_DIR)
    }

    fn ingest_file(&self, source: &Path) -> RlabResult<StoredArtifact> {
        let digest = sha256_file(source)?;
        let object_path = self.blob_path(&digest)?;
        if !object_path.exists() {
            ensure_parent_dir(&object_path)?;
            copy_file_fast(source, &object_path)?;
        }
        let size_bytes = source
            .metadata()
            .map_err(|error| RlabError::io(source, error))?
            .len();
        Ok(StoredArtifact {
            sha256: digest,
            storage_type: ArtifactStorageType::File,
            object_path,
            source_path: source.to_path_buf(),
            size_bytes,
        })
    }

    fn ingest_directory(&self, source: &Path) -> RlabResult<StoredArtifact> {
        let mut entries = Vec::new();
        for item in WalkDir::new(source).sort_by_file_name().into_iter() {
            let item = item.map_err(|error| RlabError::Io {
                path: source.to_path_buf(),
                message: error.to_string(),
            })?;
            if !item.file_type().is_file() {
                continue;
            }
            let file_path = item.path();
            let relative = file_path
                .strip_prefix(source)
                .map_err(|error| RlabError::Artifact {
                    message: error.to_string(),
                })?;
            let stored = self.ingest_file(file_path)?;
            let metadata = file_path
                .metadata()
                .map_err(|error| RlabError::io(file_path, error))?;
            let mode = file_mode(&metadata);
            entries.push(TreeEntry {
                path: relative_to_string(relative)?,
                sha256: stored.sha256,
                size_bytes: metadata.len(),
                mode,
                executable: mode & 0o111 != 0,
            });
        }
        entries.sort_by(|left, right| left.path.cmp(&right.path));
        let digest = tree_digest(&entries)?;
        let tree = TreeManifest {
            schema_version: TREE_SCHEMA_VERSION,
            digest: digest.clone(),
            entries,
        };
        let tree_path = self.tree_path(&digest);
        if !tree_path.exists() {
            ensure_parent_dir(&tree_path)?;
            write_json_atomic(&tree_path, &tree)?;
        }
        Ok(StoredArtifact {
            sha256: digest,
            storage_type: ArtifactStorageType::Directory,
            object_path: tree_path,
            source_path: source.to_path_buf(),
            size_bytes: tree.entries.iter().map(|entry| entry.size_bytes).sum(),
        })
    }

    fn materialize_tree(&self, manifest: &ArtifactManifest) -> RlabResult<PathBuf> {
        let target = self.materialized_root().join(&manifest.sha256);
        let done = target.join(".rlab-materialized");
        if done.is_file() {
            return Ok(target);
        }
        let tmp = self.materialized_root().join(format!(
            "{}.tmp-{}",
            manifest.sha256,
            std::process::id()
        ));
        if tmp.exists() {
            fs::remove_dir_all(&tmp).map_err(|error| RlabError::io(&tmp, error))?;
        }
        ensure_dir(&tmp)?;
        let tree = self.read_tree_manifest(&manifest.object_path)?;
        for entry in tree.entries {
            let relative = PathBuf::from(&entry.path);
            let destination = ensure_child_path(&tmp, &relative)?;
            ensure_parent_dir(&destination)?;
            copy_file_fast(&self.blob_path(&entry.sha256)?, &destination)?;
            set_file_mode(&destination, entry.mode)?;
        }
        write_text_atomic(&done_for(&tmp), &manifest.sha256)?;
        if target.exists() {
            fs::remove_dir_all(&tmp).map_err(|error| RlabError::io(&tmp, error))?;
        } else {
            fs::rename(&tmp, &target).map_err(|error| RlabError::io(&target, error))?;
        }
        Ok(target)
    }

    fn read_tree_manifest(&self, path: &Path) -> RlabResult<TreeManifest> {
        let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
        serde_json::from_str(&content).map_err(RlabError::serialization)
    }

    fn blob_path(&self, digest: &str) -> RlabResult<PathBuf> {
        let digest = DigestParts::parse(digest)?;
        Ok(self
            .root
            .join(OBJECTS_DIR)
            .join(BLOBS_DIR)
            .join(digest.prefix)
            .join(digest.full))
    }

    fn tree_path(&self, digest: &str) -> PathBuf {
        self.root
            .join(OBJECTS_DIR)
            .join(TREES_DIR)
            .join(format!("{digest}.json"))
    }

    fn write_manifest(&self, manifest: &ArtifactManifest) -> RlabResult<()> {
        let path = self.manifest_path(&manifest.reference);
        ensure_parent_dir(&path)?;
        write_json_atomic(&path, manifest)
    }

    fn manifest_path(&self, reference: &ArtifactReference) -> PathBuf {
        self.root
            .join(&reference.kind)
            .join(manifest_file_name(&reference.name, &reference.version))
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

    fn resolve_version(
        &self,
        kind: &str,
        name: &str,
        version_or_alias: &str,
    ) -> RlabResult<String> {
        let manifest = self
            .root
            .join(kind)
            .join(manifest_file_name(name, version_or_alias));
        if manifest.is_file() {
            return Ok(version_or_alias.to_string());
        }
        let alias = self.root.join(kind).join(name).join(version_or_alias);
        match fs::read_to_string(&alias) {
            Ok(version) => {
                let trimmed = version.trim();
                if trimmed.is_empty() {
                    return Err(artifact_error(format!(
                        "artifact alias is empty: {}",
                        alias.display()
                    )));
                }
                Ok(trimmed.to_string())
            }
            Err(error) => Err(RlabError::io(&alias, error)),
        }
    }

    fn alias_path(&self, reference: &ArtifactReference, alias: &str) -> PathBuf {
        self.root
            .join(&reference.kind)
            .join(&reference.name)
            .join(alias)
    }
}

fn done_for(path: &Path) -> PathBuf {
    path.join(".rlab-materialized")
}

struct DigestParts<'a> {
    prefix: &'a str,
    full: &'a str,
}

impl<'a> DigestParts<'a> {
    fn parse(digest: &'a str) -> RlabResult<Self> {
        let prefix = digest
            .get(..DIGEST_PREFIX_BYTES)
            .ok_or_else(|| artifact_error("invalid digest prefix"))?;
        if digest
            .get(DIGEST_PREFIX_BYTES..)
            .is_none_or(|value| value.is_empty())
        {
            return Err(artifact_error("invalid digest body"));
        }
        Ok(Self {
            prefix,
            full: digest,
        })
    }
}

fn tree_digest(entries: &[TreeEntry]) -> RlabResult<String> {
    let bytes = serde_json::to_vec(entries).map_err(RlabError::serialization)?;
    Ok(sha256_bytes(&bytes))
}

fn manifest_file_name(name: &str, version: &str) -> String {
    format!("{name}@{version}.{MANIFEST_EXTENSION}")
}

fn validate_required_artifact_fields(request: &PromoteRequest) -> RlabResult<()> {
    if is_blank(&request.artifact_kind) || is_blank(&request.name) {
        return Err(artifact_error("artifact kind and name are required"));
    }
    Ok(())
}

fn relative_to_string(path: &Path) -> RlabResult<String> {
    path.to_str()
        .map(|value| value.replace('\\', "/"))
        .ok_or_else(|| artifact_error(format!("artifact path is not UTF-8: {}", path.display())))
}

#[cfg(unix)]
fn file_mode(metadata: &fs::Metadata) -> u32 {
    use std::os::unix::fs::PermissionsExt;
    metadata.permissions().mode()
}

#[cfg(not(unix))]
fn file_mode(_metadata: &fs::Metadata) -> u32 {
    0o644
}

#[cfg(unix)]
fn set_file_mode(path: &Path, mode: u32) -> RlabResult<()> {
    use std::os::unix::fs::PermissionsExt;
    fs::set_permissions(path, fs::Permissions::from_mode(mode))
        .map_err(|error| RlabError::io(path, error))
}

#[cfg(not(unix))]
fn set_file_mode(_path: &Path, _mode: u32) -> RlabResult<()> {
    Ok(())
}

fn ensure_parent_dir(path: &Path) -> RlabResult<()> {
    match path.parent() {
        Some(parent) => ensure_dir(parent),
        None => Ok(()),
    }
}

fn copy_dir_recursive(source: &Path, target: &Path) -> RlabResult<()> {
    ensure_dir(target)?;
    for item in WalkDir::new(source).sort_by_file_name().into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: source.to_path_buf(),
            message: error.to_string(),
        })?;
        if item.path() == source {
            continue;
        }
        let relative = item
            .path()
            .strip_prefix(source)
            .map_err(|error| RlabError::Artifact {
                message: error.to_string(),
            })?;
        let destination = ensure_child_path(target, relative)?;
        if item.file_type().is_dir() {
            ensure_dir(&destination)?;
        } else if item.file_type().is_file() {
            ensure_parent_dir(&destination)?;
            copy_file_fast(item.path(), &destination)?;
        }
    }
    Ok(())
}

fn copy_file_fast(source: &Path, destination: &Path) -> RlabResult<()> {
    if clone_file(source, destination).is_ok() {
        return Ok(());
    }
    fs::copy(source, destination)
        .map(|_| ())
        .map_err(|error| RlabError::io(destination, error))
}

#[cfg(target_os = "macos")]
fn clone_file(source: &Path, destination: &Path) -> std::io::Result<()> {
    use std::ffi::CString;
    use std::os::raw::c_char;
    use std::os::unix::ffi::OsStrExt;

    extern "C" {
        fn clonefile(src: *const c_char, dst: *const c_char, flags: u32) -> i32;
    }

    let src = CString::new(source.as_os_str().as_bytes())?;
    let dst = CString::new(destination.as_os_str().as_bytes())?;
    let result = unsafe { clonefile(src.as_ptr(), dst.as_ptr(), 0) };
    if result == 0 {
        Ok(())
    } else {
        Err(std::io::Error::last_os_error())
    }
}

#[cfg(not(target_os = "macos"))]
fn clone_file(_source: &Path, _destination: &Path) -> std::io::Result<()> {
    Err(std::io::Error::new(
        std::io::ErrorKind::Unsupported,
        "clonefile is unavailable",
    ))
}

fn is_blank(value: &str) -> bool {
    value.trim().is_empty()
}

fn artifact_error(message: impl Into<String>) -> RlabError {
    RlabError::Artifact {
        message: message.into(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn directory_digest_is_deterministic_and_deduped() {
        let root = temp_root("tree");
        let paths = ProjectPaths {
            root: root.clone(),
            runs: root.join("runs"),
            artifacts: root.join("artifacts"),
            cache: root.join("cache"),
            registry_cache: root.join("registry"),
        };
        let source = root.join("source");
        fs::create_dir_all(source.join("nested")).unwrap();
        fs::write(source.join("b.txt"), "b").unwrap();
        fs::write(source.join("nested/a.txt"), "a").unwrap();
        let store = ArtifactStore::new(&paths);

        let first = store.ingest_path(&source).unwrap();
        let second = store.ingest_path(&source).unwrap();

        assert_eq!(first.sha256, second.sha256);
        assert_eq!(first.storage_type, ArtifactStorageType::Directory);
        assert!(first.object_path.is_file());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn artifact_ref_suffix_materializes_directory() {
        let root = temp_root("resolve");
        let paths = ProjectPaths {
            root: root.clone(),
            runs: root.join("runs"),
            artifacts: root.join("artifacts"),
            cache: root.join("cache"),
            registry_cache: root.join("registry"),
        };
        let source = root.join("tokenizer");
        fs::create_dir_all(&source).unwrap();
        fs::write(source.join("tokenizer.json"), "{}").unwrap();
        let store = ArtifactStore::new(&paths);
        store
            .promote(PromoteRequest {
                source: source.clone(),
                artifact_kind: "tokenizer".to_string(),
                name: "strict".to_string(),
                version: "v1".to_string(),
                alias: Some("candidate".to_string()),
            })
            .unwrap();

        let resolved = store
            .resolve_path("artifact:tokenizer/strict@candidate/tokenizer.json")
            .unwrap();

        assert_eq!(fs::read_to_string(resolved).unwrap(), "{}");
        let _ = fs::remove_dir_all(root);
    }

    fn temp_root(label: &str) -> PathBuf {
        let unique = format!("{}-{}", std::process::id(), label);
        let root = std::env::temp_dir().join(format!("rlab-artifact-{unique}"));
        let _ = fs::remove_dir_all(&root);
        root
    }
}
