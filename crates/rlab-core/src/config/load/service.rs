use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

use super::super::discovery::find_project_root;
use super::super::model::EffectiveConfig;
use super::super::overrides::ConfigOverride;
use super::super::validate::validate_config;

const CURRENT_DIR_ERROR_PATH: &str = ".";

pub fn load_effective_config(
    root: Option<&Path>,
    overrides: &[ConfigOverride],
) -> RlabResult<EffectiveConfig> {
    let start = config_start_path(root)?;
    let project_root = find_project_root(&start)?;
    let project_name = super::infer::infer_project_name(&project_root)?;
    let mut config = EffectiveConfig::default_for(project_root.clone(), project_name);

    super::pyproject::apply_pyproject(&project_root, &mut config)?;
    super::lab_toml::apply_lab_toml(&project_root, &mut config)?;
    super::env::apply_environment(&mut config)?;
    super::overrides::apply_overrides(&mut config, overrides)?;
    super::infer::apply_inferred_modules(&project_root, &mut config);
    validate_config(&config)?;

    Ok(config)
}

fn config_start_path(root: Option<&Path>) -> RlabResult<PathBuf> {
    match root {
        Some(path) => Ok(path.to_path_buf()),
        None => current_dir(),
    }
}

fn current_dir() -> RlabResult<PathBuf> {
    std::env::current_dir().map_err(|error| RlabError::io(Path::new(CURRENT_DIR_ERROR_PATH), error))
}
