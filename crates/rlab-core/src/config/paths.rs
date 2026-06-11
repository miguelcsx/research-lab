use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

use crate::error::RlabResult;
use crate::fs::{ensure_child_path, ensure_dir};

use super::model::EffectiveConfig;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectPaths {
    pub root: PathBuf,
    pub runs: PathBuf,
    pub artifacts: PathBuf,
    pub cache: PathBuf,
    pub registry_cache: PathBuf,
}

impl ProjectPaths {
    pub fn from_config(config: &EffectiveConfig) -> RlabResult<Self> {
        let root = config.project.root.clone();

        Ok(Self {
            runs: resolve_project_path(&root, &config.paths.runs)?,
            artifacts: resolve_project_path(&root, &config.paths.artifacts)?,
            cache: resolve_project_path(&root, &config.paths.cache)?,
            registry_cache: resolve_project_path(&root, &config.paths.registry_cache)?,
            root,
        })
    }

    pub fn ensure_base_dirs(&self) -> RlabResult<()> {
        ensure_dir(&self.runs)?;
        ensure_dir(&self.artifacts)?;
        ensure_dir(&self.cache)
    }
}

fn resolve_project_path(root: &Path, value: &Path) -> RlabResult<PathBuf> {
    ensure_child_path(root, value)
}
