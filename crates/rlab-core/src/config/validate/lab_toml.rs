use crate::config::model::CONFIG_SCHEMA_VERSION;
use crate::error::{RlabError, RlabResult};

const UNSUPPORTED_LAB_SCHEMA_VERSION_PREFIX: &str = "unsupported lab.toml schema_version";

pub fn validate_lab_schema_version(schema_version: Option<u32>) -> RlabResult<()> {
    match schema_version {
        Some(version) if version != CONFIG_SCHEMA_VERSION => Err(RlabError::Config {
            message: format!("{UNSUPPORTED_LAB_SCHEMA_VERSION_PREFIX}: {version}"),
        }),
        _ => Ok(()),
    }
}
