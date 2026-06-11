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
            });
        }
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    Ok(entries)
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
