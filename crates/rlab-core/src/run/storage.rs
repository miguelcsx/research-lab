use std::fs;
use std::path::{Path, PathBuf};

use serde::Serialize;
use serde_json::Value;

use crate::artifact::{
    enforce_materialized_cap, prune_runs_keep_per_experiment, sweep_unreachable_objects,
    ArtifactStore,
};
use crate::config::{OutputRetention, ProjectPaths, StorageConfig};
use crate::error::{RlabError, RlabResult};

use super::lifecycle::restage_run_checkpoints;
use super::store::{ARTIFACTS_FILE, RUN_DIR_ARTIFACTS};

pub const RUN_DIR_OUTPUTS: &str = "outputs";
const STATUS_FILE: &str = "status.txt";

/// Outcome of applying checkpoint retention to a run's outputs.
#[derive(Debug, Default, Clone)]
pub struct RetentionReport {
    /// Checkpoint directories whose resume-only files were removed.
    pub changed: Vec<PathBuf>,
    /// Number of resume-only files removed from the run directory.
    pub removed_files: u64,
    /// Bytes removed from the run directory (does not count shared CAS blobs).
    pub removed_bytes: u64,
}

impl RetentionReport {
    pub fn is_empty(&self) -> bool {
        self.changed.is_empty()
    }
}

/// Strip resume-only files (e.g. optimizer/solver state) from a run's output
/// subdirectories according to `policy`, keeping them only where the policy says
/// so. Files promoted to the store are never lost. Returns the directories that
/// were modified so the caller can refresh their content-addressed copies. A no-op
/// unless the project configured `resume_only_globs`.
pub fn apply_output_retention(
    outputs: &Path,
    policy: &OutputRetention,
    dry_run: bool,
) -> RlabResult<RetentionReport> {
    use crate::config::ResumeStateRetention;

    let mut report = RetentionReport::default();
    if policy.resume_only_globs.is_empty()
        || matches!(policy.keep_resume_state, ResumeStateRetention::All)
        || !outputs.is_dir()
    {
        return Ok(report);
    }

    let dirs = find_resume_state_dirs(outputs, &policy.resume_only_globs)?;
    if dirs.is_empty() {
        return Ok(report);
    }

    let resume = match policy.keep_resume_state {
        ResumeStateRetention::Last => {
            resolve_resume_dir(outputs, &policy.resume_pointer, &dirs)
        }
        ResumeStateRetention::None => None,
        ResumeStateRetention::All => return Ok(report),
    };

    for dir in &dirs {
        if resume.as_ref() == Some(dir) {
            continue;
        }
        let (files, bytes) = strip_resume_only_files(dir, &policy.resume_only_globs, dry_run)?;
        if files > 0 {
            report.removed_files += files;
            report.removed_bytes += bytes;
            report.changed.push(dir.clone());
        }
    }

    Ok(report)
}

/// Immediate subdirectories of `outputs` that contain at least one resume-only file.
fn find_resume_state_dirs(outputs: &Path, globs: &[String]) -> RlabResult<Vec<PathBuf>> {
    let mut dirs = Vec::new();
    for entry in fs::read_dir(outputs).map_err(|error| RlabError::io(outputs, error))? {
        let path = entry
            .map_err(|error| RlabError::io(outputs, error))?
            .path();
        if path.is_dir() && dir_has_resume_only_file(&path, globs)? {
            dirs.push(path);
        }
    }
    dirs.sort();
    Ok(dirs)
}

fn dir_has_resume_only_file(dir: &Path, globs: &[String]) -> RlabResult<bool> {
    for entry in fs::read_dir(dir).map_err(|error| RlabError::io(dir, error))? {
        let path = entry.map_err(|error| RlabError::io(dir, error))?.path();
        if path.is_file() && file_name_matches_any(&path, globs) {
            return Ok(true);
        }
    }
    Ok(false)
}

/// Identify the resumable copy from the project's pointer file (a JSON object with
/// a `checkpoint_path` field), falling back to the most recently modified directory.
fn resolve_resume_dir(outputs: &Path, pointer: &str, dirs: &[PathBuf]) -> Option<PathBuf> {
    if let Some(target) = read_resume_pointer(outputs, pointer) {
        if let Some(found) = dirs.iter().find(|path| **path == target) {
            return Some(found.clone());
        }
    }
    dirs.iter()
        .max_by_key(|path| {
            path.metadata()
                .and_then(|meta| meta.modified())
                .ok()
        })
        .cloned()
}

fn read_resume_pointer(outputs: &Path, pointer: &str) -> Option<PathBuf> {
    if pointer.trim().is_empty() {
        return None;
    }
    let content = fs::read_to_string(outputs.join(pointer)).ok()?;
    let value: Value = serde_json::from_str(&content).ok()?;
    value
        .get("checkpoint_path")
        .and_then(Value::as_str)
        .map(PathBuf::from)
}

fn strip_resume_only_files(dir: &Path, globs: &[String], dry_run: bool) -> RlabResult<(u64, u64)> {
    let mut files = 0;
    let mut bytes = 0;
    for entry in fs::read_dir(dir).map_err(|error| RlabError::io(dir, error))? {
        let path = entry.map_err(|error| RlabError::io(dir, error))?.path();
        if !path.is_file() || !file_name_matches_any(&path, globs) {
            continue;
        }
        let size = path.metadata().map(|meta| meta.len()).unwrap_or(0);
        if !dry_run {
            fs::remove_file(&path).map_err(|error| RlabError::io(&path, error))?;
        }
        files += 1;
        bytes += size;
    }
    Ok((files, bytes))
}

fn file_name_matches_any(path: &Path, globs: &[String]) -> bool {
    let Some(name) = path.file_name().and_then(|value| value.to_str()) else {
        return false;
    };
    globs.iter().any(|pattern| glob_match(pattern, name))
}

/// Minimal filename glob supporting `*` and `?`, matched against the file name only.
fn glob_match(pattern: &str, value: &str) -> bool {
    let pattern = pattern.as_bytes();
    let value = value.as_bytes();
    let mut matched = vec![vec![false; value.len() + 1]; pattern.len() + 1];
    matched[0][0] = true;
    for row in 1..=pattern.len() {
        if pattern[row - 1] == b'*' {
            matched[row][0] = matched[row - 1][0];
        }
    }
    for row in 1..=pattern.len() {
        for col in 1..=value.len() {
            matched[row][col] = match pattern[row - 1] {
                b'*' => matched[row - 1][col] || matched[row][col - 1],
                b'?' => matched[row - 1][col - 1],
                byte => byte == value[col - 1] && matched[row - 1][col - 1],
            };
        }
    }
    matched[pattern.len()][value.len()]
}

/// Replace a completed run's content-addressed directory outputs (checkpoints)
/// with hard links to their store blobs, collapsing the run-directory copy and the
/// store into a single physical copy. Reads the run's `artifacts.jsonl` for the
/// staged tree digests. Returns the number of files relinked.
pub fn relink_run_outputs(paths: &ProjectPaths, run_dir: &Path) -> RlabResult<u64> {
    let manifest = run_dir.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE);
    let Ok(content) = fs::read_to_string(&manifest) else {
        return Ok(0);
    };
    let outputs = run_dir.join(RUN_DIR_OUTPUTS);
    let store = ArtifactStore::new(paths);
    let mut relinked = 0;
    let mut seen = std::collections::BTreeSet::new();
    for line in content.lines().filter(|line| !line.trim().is_empty()) {
        let entry: Value = serde_json::from_str(line).map_err(RlabError::serialization)?;
        if entry.get("storage_type").and_then(Value::as_str) != Some("directory") {
            continue;
        }
        let (Some(path), Some(sha)) = (
            entry.get("path").and_then(Value::as_str).map(PathBuf::from),
            entry.get("sha256").and_then(Value::as_str),
        ) else {
            continue;
        };
        if !path.starts_with(&outputs) || !path.is_dir() || !seen.insert(path.clone()) {
            continue;
        }
        relinked += store.relink_dir_to_blobs(&path, sha)?;
    }
    Ok(relinked)
}

/// Summary of a retroactive `storage optimize` pass.
#[derive(Debug, Clone, Serialize)]
pub struct StorageOptimizeSummary {
    pub schema_version: u32,
    pub dry_run: bool,
    pub runs_scanned: u64,
    pub checkpoints_pruned: u64,
    pub optimizer_files_removed: u64,
    pub optimizer_bytes_removed: u64,
    pub files_relinked: u64,
    pub run_dirs_pruned: u64,
    pub run_bytes_reclaimed: u64,
    pub objects_swept: u64,
    pub object_bytes_reclaimed: u64,
}

/// Apply the project's storage policy retroactively to every completed run:
/// strip resume-only checkpoint files, refresh the affected content-addressed
/// checkpoints, prune runs beyond the per-experiment limit, and sweep the now
/// orphaned objects. This brings an existing `.rlab` in line with the policy that
/// new runs enforce automatically. With `dry_run`, nothing is modified and the
/// summary reports what would be reclaimed.
pub fn optimize_storage(
    paths: &ProjectPaths,
    storage: &StorageConfig,
    dry_run: bool,
) -> RlabResult<StorageOptimizeSummary> {
    let mut summary = StorageOptimizeSummary {
        schema_version: 1,
        dry_run,
        runs_scanned: 0,
        checkpoints_pruned: 0,
        optimizer_files_removed: 0,
        optimizer_bytes_removed: 0,
        files_relinked: 0,
        run_dirs_pruned: 0,
        run_bytes_reclaimed: 0,
        objects_swept: 0,
        object_bytes_reclaimed: 0,
    };

    if paths.runs.exists() {
        for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
            let run_dir = entry
                .map_err(|error| RlabError::io(&paths.runs, error))?
                .path();
            if !is_completed_run(&run_dir) {
                continue;
            }
            summary.runs_scanned += 1;
            let outputs = run_dir.join(RUN_DIR_OUTPUTS);
            let report = apply_output_retention(&outputs, &storage.outputs, dry_run)?;
            if report.is_empty() {
                continue;
            }
            summary.checkpoints_pruned += report.changed.len() as u64;
            summary.optimizer_files_removed += report.removed_files;
            summary.optimizer_bytes_removed += report.removed_bytes;
            if !dry_run {
                let manifest = run_dir.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE);
                restage_run_checkpoints(paths, &manifest, &report.changed)?;
            }
        }
    }

    // Collapse run-directory checkpoint copies into hard links to the store.
    if !dry_run && paths.runs.exists() {
        for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
            let run_dir = entry
                .map_err(|error| RlabError::io(&paths.runs, error))?
                .path();
            if is_completed_run(&run_dir) {
                summary.files_relinked += relink_run_outputs(paths, &run_dir)?;
            }
        }
    }

    let pruned = prune_runs_keep_per_experiment(paths, storage.runs.keep_per_experiment, dry_run)?;
    summary.run_dirs_pruned = pruned.removed_dirs;
    summary.run_bytes_reclaimed = pruned.removed_bytes;

    let swept = sweep_unreachable_objects(paths, dry_run)?;
    summary.objects_swept = swept.removed_files;
    summary.object_bytes_reclaimed = swept.removed_bytes;

    let evicted = enforce_materialized_cap(paths, storage.materialized.max_gb, dry_run)?;
    summary.objects_swept += evicted.removed_files;
    summary.object_bytes_reclaimed += evicted.removed_bytes;

    Ok(summary)
}

fn is_completed_run(run_dir: &Path) -> bool {
    if !run_dir.is_dir() || run_dir.join("run.lock").exists() {
        return false;
    }
    fs::read_to_string(run_dir.join(STATUS_FILE))
        .map(|status| status.trim() == "completed")
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ResumeStateRetention;

    fn policy() -> OutputRetention {
        OutputRetention {
            keep_resume_state: ResumeStateRetention::Last,
            resume_only_globs: vec!["runtime.pt".to_owned(), "*.optim".to_owned()],
            resume_pointer: "checkpoint-latest.json".to_owned(),
        }
    }

    fn write(path: &Path, bytes: &[u8]) {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, bytes).unwrap();
    }

    #[test]
    fn keeps_optimizer_only_on_resume_checkpoint() {
        let root = std::env::temp_dir().join(format!("rlab-retain-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let outputs = root.join("outputs");
        for label in ["best", "100k", "final"] {
            write(
                &outputs.join(format!("checkpoint-{label}")).join("model.safetensors"),
                b"weights",
            );
            write(
                &outputs.join(format!("checkpoint-{label}")).join("runtime.pt"),
                b"optimizer-state",
            );
        }
        let pointer = serde_json::json!({
            "checkpoint_path": outputs.join("checkpoint-final"),
            "label": "final",
        });
        write(
            &outputs.join("checkpoint-latest.json"),
            pointer.to_string().as_bytes(),
        );

        let report = apply_output_retention(&outputs, &policy(), false).unwrap();

        assert_eq!(report.removed_files, 2); // best + 100k runtime.pt
        assert!(outputs.join("checkpoint-final/runtime.pt").exists());
        assert!(!outputs.join("checkpoint-best/runtime.pt").exists());
        assert!(!outputs.join("checkpoint-100k/runtime.pt").exists());
        // weights are always preserved
        assert!(outputs.join("checkpoint-best/model.safetensors").exists());
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn keep_all_is_a_noop() {
        let root = std::env::temp_dir().join(format!("rlab-retain-all-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let outputs = root.join("outputs");
        write(&outputs.join("checkpoint-best/runtime.pt"), b"x");
        let mut keep_all = policy();
        keep_all.keep_resume_state = ResumeStateRetention::All;

        let report = apply_output_retention(&outputs, &keep_all, false).unwrap();

        assert!(report.is_empty());
        assert!(outputs.join("checkpoint-best/runtime.pt").exists());
        let _ = fs::remove_dir_all(root);
    }
}
