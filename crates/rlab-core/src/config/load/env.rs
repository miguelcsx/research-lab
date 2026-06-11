use std::path::PathBuf;

use crate::error::{RlabError, RlabResult};

use super::super::env::rlab_environment;
use super::super::model::EffectiveConfig;
use super::apply::set_cache_paths;

const ENV_PRODUCTION_STRICT: &str = "RLAB__PRODUCTION__STRICT";
const ENV_PYTHON_EXECUTABLE: &str = "RLAB__PYTHON__EXECUTABLE";
const ENV_PYTHON_RUNNER_MODULE: &str = "RLAB__PYTHON__RUNNER_MODULE";
const ENV_PATHS_RUNS: &str = "RLAB__PATHS__RUNS";
const ENV_PATHS_ARTIFACTS: &str = "RLAB__PATHS__ARTIFACTS";
const ENV_PATHS_CACHE: &str = "RLAB__PATHS__CACHE";

const BOOL_TRUE_VALUES: &[&str] = &["1", "true", "TRUE", "yes", "YES"];
const BOOL_FALSE_VALUES: &[&str] = &["0", "false", "FALSE", "no", "NO"];

pub fn apply_environment(config: &mut EffectiveConfig) -> RlabResult<()> {
    for (key, value) in rlab_environment() {
        apply_environment_value(config, &key, value)?;
    }

    Ok(())
}

fn apply_environment_value(
    config: &mut EffectiveConfig,
    key: &str,
    value: String,
) -> RlabResult<()> {
    match key {
        ENV_PRODUCTION_STRICT => {
            config.production.strict = parse_bool(&value)?;
        }
        ENV_PYTHON_EXECUTABLE => {
            config.python.executable = value;
        }
        ENV_PYTHON_RUNNER_MODULE => {
            config.python.runner_module = value;
        }
        ENV_PATHS_RUNS => {
            config.paths.runs = PathBuf::from(value);
        }
        ENV_PATHS_ARTIFACTS => {
            config.paths.artifacts = PathBuf::from(value);
        }
        ENV_PATHS_CACHE => {
            set_cache_paths(config, PathBuf::from(value));
        }
        _ => {}
    }

    Ok(())
}

fn parse_bool(value: &str) -> RlabResult<bool> {
    if BOOL_TRUE_VALUES.contains(&value) {
        return Ok(true);
    }

    if BOOL_FALSE_VALUES.contains(&value) {
        return Ok(false);
    }

    Err(RlabError::Config {
        message: format!("invalid boolean value: {value}"),
    })
}
