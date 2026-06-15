use std::fs;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use walkdir::WalkDir;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheEntry {
    pub path: String,
    pub bytes: u64,
    pub kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CacheInspection {
    pub schema_version: u32,
    pub path: String,
    pub entries: Vec<CacheEntry>,
    pub total_bytes: u64,
}

pub fn cache_path(paths: &ProjectPaths) -> PathBuf {
    paths.cache.clone()
}

pub fn cache_list(paths: &ProjectPaths) -> RlabResult<Vec<CacheEntry>> {
    if !paths.cache.exists() {
        return Ok(Vec::new());
    }
    let mut entries = Vec::new();
    for item in WalkDir::new(&paths.cache).into_iter() {
        let item = item.map_err(|error| RlabError::Io {
            path: paths.cache.clone(),
            message: error.to_string(),
        })?;
        if item.file_type().is_file() {
            let metadata = item.metadata().map_err(|error| RlabError::Io {
                path: item.path().to_path_buf(),
                message: error.to_string(),
            })?;
            entries.push(CacheEntry {
                path: item.path().display().to_string(),
                bytes: metadata.len(),
                kind: cache_kind(item.path()),
            });
        }
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(entries)
}

fn cache_kind(path: &std::path::Path) -> String {
    path.extension()
        .and_then(|value| value.to_str())
        .unwrap_or("file")
        .to_string()
}

pub fn cache_inspect(paths: &ProjectPaths) -> RlabResult<CacheInspection> {
    let entries = cache_list(paths)?;
    let total_bytes = entries.iter().map(|entry| entry.bytes).sum();
    Ok(CacheInspection {
        schema_version: SCHEMA_VERSION,
        path: paths.cache.display().to_string(),
        entries,
        total_bytes,
    })
}

pub fn clean_cache(paths: &ProjectPaths) -> RlabResult<CacheInspection> {
    if paths.cache.exists() {
        fs::remove_dir_all(&paths.cache).map_err(|error| RlabError::io(&paths.cache, error))?;
    }
    fs::create_dir_all(&paths.cache).map_err(|error| RlabError::io(&paths.cache, error))?;
    cache_inspect(paths)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::ProjectPaths;
    use std::path::Path;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn clean_cache_recreates_cache_dir() {
        let root = temp_root("recreate");
        let paths = default_paths(&root);
        let cache_file = paths.cache.join("registry.json");
        fs::create_dir_all(cache_file.parent().unwrap()).expect("create cache dir");
        fs::write(&cache_file, "{}").expect("write cache file");

        let inspection = expect_ok(clean_cache(&paths));

        assert!(paths.cache.exists());
        assert!(inspection.entries.is_empty());
        assert_eq!(inspection.total_bytes, 0);
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
        std::env::temp_dir().join(format!("rlab-cache-{label}-{unique}"))
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
