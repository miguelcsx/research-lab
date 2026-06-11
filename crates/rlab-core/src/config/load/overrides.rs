use std::path::PathBuf;

use crate::error::{RlabError, RlabResult};

use super::super::model::EffectiveConfig;
use super::super::overrides::ConfigOverride;
use super::apply::set_cache_paths;

const OVERRIDE_PATH_SEPARATOR: &str = ".";
const OVERRIDE_PRODUCTION_STRICT: &str = "production.strict";
const OVERRIDE_PYTHON_EXECUTABLE: &str = "python.executable";
const OVERRIDE_PYTHON_RUNNER_MODULE: &str = "python.runner_module";
const OVERRIDE_PATHS_RUNS: &str = "paths.runs";
const OVERRIDE_PATHS_ARTIFACTS: &str = "paths.artifacts";
const OVERRIDE_PATHS_CACHE: &str = "paths.cache";

pub fn apply_overrides(
    config: &mut EffectiveConfig,
    overrides: &[ConfigOverride],
) -> RlabResult<()> {
    for override_value in overrides {
        apply_override(config, override_value)?;
    }

    Ok(())
}

fn apply_override(config: &mut EffectiveConfig, override_value: &ConfigOverride) -> RlabResult<()> {
    let path = override_path(override_value);

    match path.as_str() {
        OVERRIDE_PRODUCTION_STRICT => {
            config.production.strict = override_bool(override_value, &path)?;
        }
        OVERRIDE_PYTHON_EXECUTABLE => {
            config.python.executable = override_string(override_value, &path)?;
        }
        OVERRIDE_PYTHON_RUNNER_MODULE => {
            config.python.runner_module = override_string(override_value, &path)?;
        }
        OVERRIDE_PATHS_RUNS => {
            config.paths.runs = PathBuf::from(override_string(override_value, &path)?);
        }
        OVERRIDE_PATHS_ARTIFACTS => {
            config.paths.artifacts = PathBuf::from(override_string(override_value, &path)?);
        }
        OVERRIDE_PATHS_CACHE => {
            set_cache_paths(
                config,
                PathBuf::from(override_string(override_value, &path)?),
            );
        }
        _ => {
            return Err(RlabError::Config {
                message: format!("unknown override path: {path}"),
            });
        }
    }

    Ok(())
}

fn override_path(override_value: &ConfigOverride) -> String {
    override_value.path.join(OVERRIDE_PATH_SEPARATOR)
}

fn override_bool(override_value: &ConfigOverride, path: &str) -> RlabResult<bool> {
    override_value
        .value
        .as_bool()
        .ok_or_else(|| RlabError::Config {
            message: format!("{path} override must be a boolean"),
        })
}

fn override_string(override_value: &ConfigOverride, path: &str) -> RlabResult<String> {
    override_value
        .value
        .as_str()
        .filter(|text| !text.trim().is_empty())
        .map(str::to_owned)
        .ok_or_else(|| RlabError::Config {
            message: format!("{path} override must be a non-empty string"),
        })
}
