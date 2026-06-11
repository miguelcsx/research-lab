mod apply;
mod env;
mod infer;
mod lab_toml;
mod overrides;
mod pyproject;
mod toml;

use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

use super::discovery::find_project_root;
use super::model::EffectiveConfig;
use super::overrides::ConfigOverride;
use super::validate::validate_config;

const CURRENT_DIR_ERROR_PATH: &str = ".";

pub fn load_effective_config(
    root: Option<&Path>,
    overrides: &[ConfigOverride],
) -> RlabResult<EffectiveConfig> {
    let start = config_start_path(root)?;
    let project_root = find_project_root(&start)?;
    let project_name = infer::infer_project_name(&project_root)?;

    let mut config = EffectiveConfig::default_for(project_root.clone(), project_name);

    pyproject::apply_pyproject(&project_root, &mut config)?;
    lab_toml::apply_lab_toml(&project_root, &mut config)?;
    env::apply_environment(&mut config)?;
    overrides::apply_overrides(&mut config, overrides)?;
    infer::apply_inferred_modules(&project_root, &mut config);

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
