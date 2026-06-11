use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

const PROJECT_MARKERS: &[&str] = &["lab.toml", "pyproject.toml", ".git"];
const CURRENT_DIR_ERROR_PATH: &str = ".";

pub fn find_project_root(start: &Path) -> RlabResult<PathBuf> {
    let canonical_start = canonical_existing_path(start)?;
    let search_start = project_search_start(&canonical_start);

    match find_nearest_project_root(search_start) {
        Some(root) => Ok(root.to_path_buf()),
        None => current_dir_fallback(),
    }
}

fn canonical_existing_path(path: &Path) -> RlabResult<PathBuf> {
    if !path.exists() {
        return Err(RlabError::NotFound {
            subject: format!("start path {}", path.display()),
        });
    }

    path.canonicalize()
        .map_err(|error| RlabError::io(path, error))
}

fn project_search_start(path: &Path) -> &Path {
    if !path.is_file() {
        return path;
    }

    match path.parent() {
        Some(parent) => parent,
        None => path,
    }
}

fn find_nearest_project_root(start: &Path) -> Option<&Path> {
    start
        .ancestors()
        .find(|candidate| is_project_root(candidate))
}

fn is_project_root(path: &Path) -> bool {
    PROJECT_MARKERS
        .iter()
        .any(|marker| path.join(marker).exists())
}

fn current_dir_fallback() -> RlabResult<PathBuf> {
    std::env::current_dir().map_err(|error| RlabError::io(Path::new(CURRENT_DIR_ERROR_PATH), error))
}
