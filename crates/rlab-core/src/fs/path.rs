use std::fs;
use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

pub fn ensure_dir(path: &Path) -> RlabResult<()> {
    fs::create_dir_all(path).map_err(|error| RlabError::io(path, error))
}

pub fn canonicalize_existing(path: &Path) -> RlabResult<PathBuf> {
    path.canonicalize().map_err(|error| RlabError::io(path, error))
}
