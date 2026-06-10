use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

pub fn find_project_root(start: &Path) -> RlabResult<PathBuf> {
    let canonical_start = if start.exists() {
        start.canonicalize().map_err(|error| RlabError::io(start, error))?
    } else {
        return Err(RlabError::NotFound {
            subject: format!("start path {}", start.display()),
        });
    };
    let mut current = if canonical_start.is_file() {
        match canonical_start.parent() {
            Some(parent) => parent.to_path_buf(),
            None => canonical_start,
        }
    } else {
        canonical_start
    };
    loop {
        if current.join("lab.toml").exists() || current.join("pyproject.toml").exists() || current.join(".git").exists() {
            return Ok(current);
        }
        match current.parent() {
            Some(parent) => current = parent.to_path_buf(),
            None => return std::env::current_dir().map_err(|error| RlabError::io(Path::new("."), error)),
        }
    }
}
