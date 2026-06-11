use crate::config::model::{EffectiveConfig, CONFIG_SCHEMA_VERSION};
use crate::error::{RlabError, RlabResult};

use super::names::validate_project_name;
use super::strings::validate_non_empty;

const PYTHON_EXECUTABLE_LABEL: &str = "python executable";
const PYTHON_RUNNER_MODULE_LABEL: &str = "python runner module";
const UNSUPPORTED_CONFIG_SCHEMA_VERSION_MESSAGE: &str = "unsupported config schema version";

pub fn validate_config(config: &EffectiveConfig) -> RlabResult<()> {
    validate_schema_version(config.schema_version)?;
    validate_project_name(&config.project.name)?;
    validate_non_empty(PYTHON_EXECUTABLE_LABEL, &config.python.executable)?;
    validate_non_empty(PYTHON_RUNNER_MODULE_LABEL, &config.python.runner_module)?;

    Ok(())
}

fn validate_schema_version(schema_version: u32) -> RlabResult<()> {
    if schema_version == CONFIG_SCHEMA_VERSION {
        return Ok(());
    }

    Err(RlabError::Config {
        message: UNSUPPORTED_CONFIG_SCHEMA_VERSION_MESSAGE.to_owned(),
    })
}
