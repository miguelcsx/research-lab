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

/// Remove content-addressed objects (blobs/trees) that are no longer reachable
/// from any artifact manifest or completed run, without touching the regenerable
/// `materialized/` cache. Used after a run rewrites its checkpoints so orphaned
/// optimizer-state blobs are reclaimed immediately.
pub fn sweep_unreachable_objects(paths: &ProjectPaths, dry_run: bool) -> RlabResult<GcSummary> {
    let store = ArtifactStore::new(paths);
    let mut summary = GcSummary {
        schema_version: 1,
        dry_run,
        removed_files: 0,
        removed_dirs: 0,
        removed_bytes: 0,
    };
    let reachable = reachable_objects(paths)?;
    remove_unreachable_files(&store.object_root(), &reachable, dry_run, &mut summary)?;
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
/// Keep at most `keep` of the most recent runs per experiment name, pruning the
/// rest. Only runs whose durable checkpoints are already stored in the
/// content-addressed store are eligible: pruning such a run reclaims space
/// without losing a checkpoint, while lightweight runs (evaluations, reports)
/// whose only outputs are their own `results.json`/metrics are left untouched.
/// Runs holding a `run.lock` are always preserved.
pub fn prune_runs_keep_per_experiment(
    paths: &ProjectPaths,
    keep: u32,
    dry_run: bool,
) -> RlabResult<GcSummary> {
    let mut summary = GcSummary {
        schema_version: 1,
        dry_run,
        removed_files: 0,
        removed_dirs: 0,
        removed_bytes: 0,
    };
    if keep == 0 || !paths.runs.exists() {
        return Ok(summary);
    }

    // Group prunable runs by experiment name, recording (created_at, path).
    let mut groups: std::collections::BTreeMap<String, Vec<(String, PathBuf)>> =
        std::collections::BTreeMap::new();
    for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
        let path = entry
            .map_err(|error| RlabError::io(&paths.runs, error))?
            .path();
        if !path.is_dir() || path.join("run.lock").exists() || !run_has_promoted_artifact(&path) {
            continue;
        }
        let Some((name, created_at)) = read_run_identity(&path) else {
            continue;
        };
        groups.entry(name).or_default().push((created_at, path));
    }

    for runs in groups.values_mut() {
        if runs.len() as u32 <= keep {
            continue;
        }
        // Most recent first; keep the first `keep`, prune the remainder.
        runs.sort_by(|left, right| right.0.cmp(&left.0));
        for (_, path) in runs.iter().skip(keep as usize) {
            let before = inspect_tree(path)?;
            if !dry_run {
                fs::remove_dir_all(path).map_err(|error| RlabError::io(path, error))?;
            }
            summary.removed_files += before.files;
            summary.removed_dirs += before.dirs + 1;
            summary.removed_bytes += before.bytes;
        }
    }

    Ok(summary)
}

/// Bound the regenerable `materialized/` cache to `max_gb`, evicting the least
/// recently modified entries until the total falls under the limit. A `max_gb` of
/// `0` disables the cap. Materialized trees can always be rebuilt from the store,
/// so eviction never loses data.
pub fn enforce_materialized_cap(
    paths: &ProjectPaths,
    max_gb: u32,
    dry_run: bool,
) -> RlabResult<GcSummary> {
    let mut summary = GcSummary {
        schema_version: 1,
        dry_run,
        removed_files: 0,
        removed_dirs: 0,
        removed_bytes: 0,
    };
    let root = ArtifactStore::new(paths).materialized_root();
    if max_gb == 0 || !root.exists() {
        return Ok(summary);
    }
    let cap = u64::from(max_gb) * 1024 * 1024 * 1024;

    // Collect entries with their size and recency (modified time).
    let mut entries = Vec::new();
    let mut total = 0u64;
    for entry in fs::read_dir(&root).map_err(|error| RlabError::io(&root, error))? {
        let path = entry.map_err(|error| RlabError::io(&root, error))?.path();
        let inspection = inspect_tree(&path)?;
        total += inspection.bytes;
        let modified = path
            .metadata()
            .and_then(|meta| meta.modified())
            .unwrap_or(SystemTime::UNIX_EPOCH);
        entries.push((modified, path, inspection));
    }
    if total <= cap {
        return Ok(summary);
    }

    // Evict oldest-first until under the cap.
    entries.sort_by_key(|(modified, _, _)| *modified);
    for (_, path, inspection) in entries {
        if total <= cap {
            break;
        }
        if !dry_run {
            fs::remove_dir_all(&path).map_err(|error| RlabError::io(&path, error))?;
        }
        total = total.saturating_sub(inspection.bytes);
        summary.removed_files += inspection.files;
        summary.removed_dirs += inspection.dirs + 1;
        summary.removed_bytes += inspection.bytes;
    }
    Ok(summary)
}

/// A run is safe to prune only when it has promoted at least one durable artifact
/// (of any kind) to the content-addressed store, so removing its directory cannot
/// lose that output. Lightweight runs whose results live only in the run directory
/// (e.g. evaluations or reports) never match and are therefore preserved.
fn run_has_promoted_artifact(run_dir: &Path) -> bool {
    let manifest = run_dir.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE);
    let Ok(content) = fs::read_to_string(&manifest) else {
        return false;
    };
    content
        .lines()
        .filter(|line| !line.trim().is_empty())
        .any(|line| {
            serde_json::from_str::<Value>(line)
                .ok()
                .is_some_and(|entry| {
                    let has_semantic_kind =
                        entry.get("artifact_kind").and_then(Value::as_str).is_some();
                    let has_object =
                        entry.get("object_path").and_then(Value::as_str).is_some();
                    has_semantic_kind && has_object
                })
        })
}

/// Read a run's experiment name and creation timestamp from its `run.json`.
fn read_run_identity(run_dir: &Path) -> Option<(String, String)> {
    let content = fs::read_to_string(run_dir.join("run.json")).ok()?;
    let value: Value = serde_json::from_str(&content).ok()?;
    let name = value.get("name").and_then(Value::as_str)?.to_string();
    let created_at = value
        .get("created_at")
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_string();
    Some((name, created_at))
}

fn reachable_objects(paths: &ProjectPaths) -> RlabResult<BTreeSet<PathBuf>> {
    let mut reachable = BTreeSet::new();
    let store = ArtifactStore::new(paths);
    // `index.jsonl` is append-only, so a re-promoted artifact (e.g. a checkpoint
    // rewritten to drop optimizer state) leaves a stale row pointing at the old
    // object. Keep only the latest row per (kind, name, version) — which matches
    // the authoritative on-disk manifest — so superseded objects can be reclaimed.
    let mut latest: std::collections::BTreeMap<(String, String, String), ArtifactManifest> =
        std::collections::BTreeMap::new();
    for manifest in store.list(None, None, None)? {
        let key = (
            manifest.reference.kind.clone(),
            manifest.reference.name.clone(),
            manifest.reference.version.clone(),
        );
        latest.insert(key, manifest);
    }
    for manifest in latest.values() {
        insert_manifest(&mut reachable, manifest)?;
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

#[cfg(test)]
mod tests {
    use super::*;

    fn paths_at(root: &Path) -> ProjectPaths {
        ProjectPaths {
            root: root.to_path_buf(),
            runs: root.join("runs"),
            artifacts: root.join("artifacts"),
            cache: root.join("cache"),
            registry_cache: root.join("registry"),
        }
    }

    fn make_run(runs: &Path, name: &str, created_at: &str, locked: bool) {
        make_run_kind(runs, name, created_at, locked, true);
    }

    fn make_run_kind(runs: &Path, name: &str, created_at: &str, locked: bool, checkpoint: bool) {
        let dir = runs.join(format!("{name}_{created_at}"));
        fs::create_dir_all(dir.join(RUN_DIR_ARTIFACTS)).unwrap();
        fs::write(
            dir.join("run.json"),
            serde_json::json!({ "name": name, "created_at": created_at }).to_string(),
        )
        .unwrap();
        fs::write(dir.join("payload.bin"), vec![0u8; 16]).unwrap();
        // Only runs with a checkpoint promoted to the CAS are prunable.
        let entry = if checkpoint {
            serde_json::json!({ "artifact_kind": "checkpoint", "object_path": "/cas/tree.json" })
        } else {
            serde_json::json!({ "kind": "file", "object_path": "/cas/metrics" })
        };
        fs::write(
            dir.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE),
            format!("{entry}\n"),
        )
        .unwrap();
        if locked {
            fs::write(dir.join("run.lock"), "").unwrap();
        }
    }

    #[test]
    fn keeps_newest_n_per_experiment_and_preserves_locked() {
        let root = std::env::temp_dir().join(format!("rlab-gc-keep-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let paths = paths_at(&root);
        fs::create_dir_all(&paths.runs).unwrap();

        // Three runs of experiment A (keep 2 newest), one of B, one locked old A.
        make_run(&paths.runs, "exp.a", "2026-06-01T00:00:00Z", false);
        make_run(&paths.runs, "exp.a", "2026-06-02T00:00:00Z", false);
        make_run(&paths.runs, "exp.a", "2026-06-03T00:00:00Z", false);
        make_run(&paths.runs, "exp.a", "2026-05-01T00:00:00Z", true); // locked: always kept
        make_run(&paths.runs, "exp.b", "2026-06-01T00:00:00Z", false);

        let summary = prune_runs_keep_per_experiment(&paths, 2, false).unwrap();
        assert!(summary.removed_dirs >= 1);

        // Oldest unlocked exp.a run pruned; newest two and the locked one remain.
        assert!(!paths.runs.join("exp.a_2026-06-01T00:00:00Z").exists());
        assert!(paths.runs.join("exp.a_2026-06-02T00:00:00Z").exists());
        assert!(paths.runs.join("exp.a_2026-06-03T00:00:00Z").exists());
        assert!(paths.runs.join("exp.a_2026-05-01T00:00:00Z").exists());
        assert!(paths.runs.join("exp.b_2026-06-01T00:00:00Z").exists());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn never_prunes_runs_without_cas_checkpoints() {
        let root = std::env::temp_dir().join(format!("rlab-gc-eval-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let paths = paths_at(&root);
        fs::create_dir_all(&paths.runs).unwrap();
        // Many eval runs (no checkpoint in CAS) must all survive despite keep=1.
        for day in 1..=5 {
            make_run_kind(
                &paths.runs,
                "eval.babylm",
                &format!("2026-06-0{day}T00:00:00Z"),
                false,
                false,
            );
        }

        let summary = prune_runs_keep_per_experiment(&paths, 1, false).unwrap();
        assert_eq!(summary.removed_dirs, 0);
        for day in 1..=5 {
            assert!(paths
                .runs
                .join(format!("eval.babylm_2026-06-0{day}T00:00:00Z"))
                .exists());
        }
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn keep_zero_disables_pruning() {
        let root = std::env::temp_dir().join(format!("rlab-gc-keep0-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let paths = paths_at(&root);
        fs::create_dir_all(&paths.runs).unwrap();
        make_run(&paths.runs, "exp.a", "2026-06-01T00:00:00Z", false);
        make_run(&paths.runs, "exp.a", "2026-06-02T00:00:00Z", false);

        let summary = prune_runs_keep_per_experiment(&paths, 0, false).unwrap();
        assert_eq!(summary.removed_dirs, 0);
        assert!(paths.runs.join("exp.a_2026-06-01T00:00:00Z").exists());
        let _ = fs::remove_dir_all(root);
    }
}
