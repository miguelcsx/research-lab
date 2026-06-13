use crate::error::{RlabError, RlabResult};

use super::name::RegistryName;
use super::record::RegistryRecord;
use super::schema::REGISTRY_SCHEMA_VERSION;

pub fn validate_registry_record(record: &RegistryRecord) -> RlabResult<()> {
    validate_schema_version(record.schema_version)?;
    record.kind.validate()?;
    RegistryName::parse(&record.name)?;
    validate_non_empty_field(&record.name, "version", &record.version)?;
    validate_non_empty_field(&record.name, "module", &record.module)?;
    validate_non_empty_field(&record.name, "qualname", &record.qualname)?;

    Ok(())
}

fn validate_schema_version(schema_version: u32) -> RlabResult<()> {
    if schema_version == REGISTRY_SCHEMA_VERSION {
        return Ok(());
    }

    Err(RlabError::registry("unsupported registry schema version"))
}

fn validate_non_empty_field(record_name: &str, field: &str, value: &str) -> RlabResult<()> {
    if !value.trim().is_empty() {
        return Ok(());
    }

    Err(RlabError::registry(format!(
        "record {record_name} has empty {field}"
    )))
}
