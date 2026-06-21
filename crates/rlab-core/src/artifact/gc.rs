use std::collections::BTreeSet;
use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, SystemTime};

use serde::{Deserialize, Serialize};
use serde_json::Value;
use walkdir::WalkDir;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::run::{RunStatus, ARTIFACTS_FILE, RUN_DIR_ARTIFACTS};

use super::manifest::ArtifactManifest;
use super::store::ArtifactStore;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GcSummary {
    pub schema_version: u32,
    pub dry_run: bool,
    pub removed_files: u64,
    pub removed_dirs: u64,
    pub removed_bytes: u64,
}

pub fn gc_artifacts(
    paths: &ProjectPaths,
    dry_run: bool,
    materialized_only: bool,
) -> RlabResult<GcSummary> {
    let store = ArtifactStore::new(paths);
    let mut summary = GcSummary {
        schema_version: 1,
        dry_run,
        removed_files: 0,
        removed_dirs: 0,
        removed_bytes: 0,
    };
    if materialized_only {
        remove_children(&store.materialized_root(), dry_run, &mut summary)?;
        return Ok(summary);
    }
    let reachable = reachable_objects(paths)?;
    remove_unreachable_files(&store.object_root(), &reachable, dry_run, &mut summary)?;
    remove_children(&store.materialized_root(), dry_run, &mut summary)?;
    Ok(summary)
}

pub fn prune_runs(
    paths: &ProjectPaths,
    dry_run: bool,
    older_than: Duration,
) -> RlabResult<GcSummary> {
    let mut summary = GcSummary {
        schema_version: 1,
        dry_run,
        removed_files: 0,
        removed_dirs: 0,
        removed_bytes: 0,
    };
    if !paths.runs.exists() {
        return Ok(summary);
    }
    let cutoff = SystemTime::now()
        .checked_sub(older_than)
        .ok_or_else(|| RlabError::validation("invalid gc --older-than duration"))?;
    for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
        let path = entry
            .map_err(|error| RlabError::io(&paths.runs, error))?
            .path();
        if !path.is_dir() || path.join("run.lock").exists() {
            continue;
        }
        let metadata = path
            .metadata()
            .map_err(|error| RlabError::io(&path, error))?;
        let modified = metadata
            .modified()
            .map_err(|error| RlabError::io(&path, error))?;
        if modified > cutoff {
            continue;
        }
        let before = inspect_tree(&path)?;
        if !dry_run {
            fs::remove_dir_all(&path).map_err(|error| RlabError::io(&path, error))?;
        }
        summary.removed_files += before.files;
        summary.removed_dirs += before.dirs + 1;
        summary.removed_bytes += before.bytes;
    }
    Ok(summary)
}
fn reachable_objects(paths: &ProjectPaths) -> RlabResult<BTreeSet<PathBuf>> {
    let mut reachable = BTreeSet::new();
    let store = ArtifactStore::new(paths);
    for manifest in store.list(None, None, None)? {
        insert_manifest(&mut reachable, &manifest)?;
    }
    if paths.runs.exists() {
        for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
            let path = entry
                .map_err(|error| RlabError::io(&paths.runs, error))?
                .path();
            if !path.is_dir() || path.join("run.lock").exists() {
                continue;
            }
            let status = fs::read_to_string(path.join("status.txt")).unwrap_or_default();
            if status.trim() != RunStatus::Completed.as_str() {
                continue;
            }
            let artifacts = path.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE);
            if !artifacts.exists() {
                continue;
            }
            for line in fs::read_to_string(&artifacts)
                .map_err(|error| RlabError::io(&artifacts, error))?
                .lines()
            {
                if line.trim().is_empty() {
                    continue;
                }
                let value: Value = serde_json::from_str(line).map_err(RlabError::serialization)?;
                if let Some(path) = value.get("object_path").and_then(Value::as_str) {
                    insert_object_path(&mut reachable, PathBuf::from(path))?;
                }
            }
        }
    }
    Ok(reachable)
}

fn insert_manifest(
    reachable: &mut BTreeSet<PathBuf>,
    manifest: &ArtifactManifest,
) -> RlabResult<()> {
    insert_object_path(reachable, manifest.object_path.clone())
}

fn insert_object_path(reachable: &mut BTreeSet<PathBuf>, object_path: PathBuf) -> RlabResult<()> {
    reachable.insert(object_path.clone());
    if object_path
        .parent()
        .and_then(Path::file_name)
        .and_then(|value| value.to_str())
        != Some("trees")
    {
        return Ok(());
    }
    let content =
        fs::read_to_string(&object_path).map_err(|error| RlabError::io(&object_path, error))?;
    let value: Value = serde_json::from_str(&content).map_err(RlabError::serialization)?;
    let Some(objects_root) = object_path.parent().and_then(Path::parent) else {
        return Ok(());
    };
    if let Some(entries) = value.get("entries").and_then(Value::as_array) {
        for entry in entries {
            if let Some(sha) = entry.get("sha256").and_then(Value::as_str) {
                if sha.len() >= 2 {
                    reachable.insert(objects_root.join("blobs").join(&sha[..2]).join(sha));
                }
            }
        }
    }
    Ok(())
}

fn remove_unreachable_files(
    root: &Path,
    reachable: &BTreeSet<PathBuf>,
    dry_run: bool,
    summary: &mut GcSummary,
) -> RlabResult<()> {
    if !root.exists() {
        return Ok(());
    }
    let mut files = Vec::new();
    for item in WalkDir::new(root).contents_first(true).into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: root.to_path_buf(),
            message: error.to_string(),
        })?;
        if item.file_type().is_file() {
            let path = item.path().to_path_buf();
            if !reachable.contains(&path) {
                files.push(path);
            }
        }
    }
    for file in files {
        let bytes = file.metadata().map(|m| m.len()).unwrap_or(0);
        if !dry_run {
            fs::remove_file(&file).map_err(|error| RlabError::io(&file, error))?;
        }
        summary.removed_files += 1;
        summary.removed_bytes += bytes;
    }
    remove_empty_dirs(root, dry_run, summary)
}

fn remove_children(root: &Path, dry_run: bool, summary: &mut GcSummary) -> RlabResult<()> {
    if !root.exists() {
        return Ok(());
    }
    for entry in fs::read_dir(root).map_err(|error| RlabError::io(root, error))? {
        let path = entry.map_err(|error| RlabError::io(root, error))?.path();
        let before = inspect_tree(&path)?;
        if !dry_run {
            if path.is_dir() {
                fs::remove_dir_all(&path).map_err(|error| RlabError::io(&path, error))?;
            } else {
                fs::remove_file(&path).map_err(|error| RlabError::io(&path, error))?;
            }
        }
        summary.removed_files += before.files;
        summary.removed_dirs += before.dirs + u64::from(path.is_dir());
        summary.removed_bytes += before.bytes;
    }
    Ok(())
}

fn remove_empty_dirs(root: &Path, dry_run: bool, summary: &mut GcSummary) -> RlabResult<()> {
    if !root.exists() {
        return Ok(());
    }
    let mut dirs = Vec::new();
    for item in WalkDir::new(root).contents_first(true).into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: root.to_path_buf(),
            message: error.to_string(),
        })?;
        if item.file_type().is_dir() && item.path() != root {
            dirs.push(item.path().to_path_buf());
        }
    }
    for dir in dirs {
        if fs::read_dir(&dir)
            .map_err(|error| RlabError::io(&dir, error))?
            .next()
            .is_none()
        {
            if !dry_run {
                fs::remove_dir(&dir).map_err(|error| RlabError::io(&dir, error))?;
            }
            summary.removed_dirs += 1;
        }
    }
    Ok(())
}

#[derive(Default)]
struct Inspection {
    files: u64,
    dirs: u64,
    bytes: u64,
}

fn inspect_tree(path: &Path) -> RlabResult<Inspection> {
    if !path.exists() {
        return Ok(Inspection::default());
    }
    let mut out = Inspection::default();
    for item in WalkDir::new(path).into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: path.to_path_buf(),
            message: error.to_string(),
        })?;
        if item.file_type().is_file() {
            out.files += 1;
            out.bytes += item
                .metadata()
                .map_err(|error| RlabError::io(item.path(), error.into()))?
                .len();
        } else if item.file_type().is_dir() && item.path() != path {
            out.dirs += 1;
        }
    }
    Ok(out)
}
