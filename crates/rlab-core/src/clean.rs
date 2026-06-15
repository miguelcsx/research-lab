use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use walkdir::WalkDir;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::ensure_child_path;

const SCHEMA_VERSION: u32 = 1;
const RUNTIME_DIR: &str = ".rlab";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CleanSummary {
    pub schema_version: u32,
    pub path: String,
    pub removed: bool,
    pub before_files: u64,
    pub before_bytes: u64,
    pub after_files: u64,
    pub after_bytes: u64,
}

pub fn clean_project_state(paths: &ProjectPaths, force: bool) -> RlabResult<CleanSummary> {
    let runtime_root = project_runtime_root(paths)?;
    ensure_runtime_paths_under_root(paths, &runtime_root)?;

    let before = inspect_tree(&runtime_root)?;
    let removed = force && runtime_root.exists();
    if removed {
        fs::remove_dir_all(&runtime_root).map_err(|error| RlabError::io(&runtime_root, error))?;
    }
    let after = inspect_tree(&runtime_root)?;

    Ok(CleanSummary {
        schema_version: SCHEMA_VERSION,
        path: runtime_root.display().to_string(),
        removed,
        before_files: before.files,
        before_bytes: before.bytes,
        after_files: after.files,
        after_bytes: after.bytes,
    })
}

fn project_runtime_root(paths: &ProjectPaths) -> RlabResult<PathBuf> {
    ensure_child_path(&paths.root, Path::new(RUNTIME_DIR))
}

fn ensure_runtime_paths_under_root(paths: &ProjectPaths, runtime_root: &Path) -> RlabResult<()> {
    for path in [
        &paths.runs,
        &paths.artifacts,
        &paths.cache,
        &paths.registry_cache,
    ] {
        if !path.starts_with(runtime_root) {
            return Err(RlabError::validation(format!(
                "rlab clean only removes project-local .rlab state; configured path is outside .rlab: {}",
                path.display()
            )));
        }
    }
    Ok(())
}

#[derive(Debug, Clone, Copy)]
struct TreeInspection {
    files: u64,
    bytes: u64,
}

fn inspect_tree(root: &Path) -> RlabResult<TreeInspection> {
    if !root.exists() {
        return Ok(TreeInspection { files: 0, bytes: 0 });
    }

    let mut inspection = TreeInspection { files: 0, bytes: 0 };
    for item in WalkDir::new(root).into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: root.to_path_buf(),
            message: error.to_string(),
        })?;
        if item.file_type().is_file() {
            let metadata = item.metadata().map_err(|error| RlabError::Io {
                path: item.path().to_path_buf(),
                message: error.to_string(),
            })?;
            inspection.files += 1;
            inspection.bytes += metadata.len();
        }
    }
    Ok(inspection)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ProjectPaths;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn clean_missing_runtime_dir_succeeds() {
        let root = temp_root("missing");
        let paths = default_paths(&root);

        let summary = expect_ok(clean_project_state(&paths, true));

        assert!(!summary.removed);
        assert_eq!(summary.before_files, 0);
        assert_eq!(summary.after_files, 0);
        assert!(!root.join(".rlab").exists());
        cleanup(root);
    }

    #[test]
    fn clean_populated_runtime_dir_removes_with_force() {
        let root = temp_root("populated");
        let paths = default_paths(&root);
        let run_file = root.join(".rlab/runs/run-1/metrics.jsonl");
        fs::create_dir_all(run_file.parent().unwrap()).expect("create run dir");
        fs::write(&run_file, "metric").expect("write run file");

        let summary = expect_ok(clean_project_state(&paths, true));

        assert!(summary.removed);
        assert_eq!(summary.before_files, 1);
        assert_eq!(summary.before_bytes, 6);
        assert_eq!(summary.after_files, 0);
        assert_eq!(summary.after_bytes, 0);
        assert!(!root.join(".rlab").exists());
        cleanup(root);
    }

    #[test]
    fn clean_without_force_reports_without_removing() {
        let root = temp_root("dry-run");
        let paths = default_paths(&root);
        let cache_file = root.join(".rlab/cache/registry.json");
        fs::create_dir_all(cache_file.parent().unwrap()).expect("create cache dir");
        fs::write(&cache_file, "{}").expect("write cache file");

        let summary = expect_ok(clean_project_state(&paths, false));

        assert!(!summary.removed);
        assert_eq!(summary.before_files, 1);
        assert_eq!(summary.after_files, 1);
        assert!(root.join(".rlab").exists());
        cleanup(root);
    }

    #[test]
    fn rejects_configured_paths_outside_default_runtime_dir() {
        let root = temp_root("outside");
        let mut paths = default_paths(&root);
        paths.cache = root.join("cache");

        assert!(clean_project_state(&paths, true).is_err());
        cleanup(root);
    }

    fn default_paths(root: &Path) -> ProjectPaths {
        ProjectPaths {
            root: root.to_path_buf(),
            runs: root.join(".rlab/runs"),
            artifacts: root.join(".rlab/artifacts"),
            cache: root.join(".rlab/cache"),
            registry_cache: root.join(".rlab/cache/registry.json"),
        }
    }

    fn temp_root(label: &str) -> PathBuf {
        let unique = match SystemTime::now().duration_since(UNIX_EPOCH) {
            Ok(duration) => duration.as_nanos(),
            Err(_) => 0,
        };
        std::env::temp_dir().join(format!("rlab-clean-{label}-{unique}"))
    }

    fn cleanup(root: PathBuf) {
        if root.exists() {
            fs::remove_dir_all(root).expect("remove temp root");
        }
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected ok, got {error}"),
        }
    }
}
