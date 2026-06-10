use crate::error::{RlabError, RlabResult};

use super::name::RegistryName;
use super::record::RegistryRecord;
use super::schema::REGISTRY_SCHEMA_VERSION;

pub fn validate_registry_record(record: &RegistryRecord) -> RlabResult<()> {
    if record.schema_version != REGISTRY_SCHEMA_VERSION {
        return Err(RlabError::Registry { message: "unsupported registry schema version".to_string() });
    }
    RegistryName::parse(&record.name)?;
    if record.version.trim().is_empty() {
        return Err(RlabError::Registry { message: format!("record {} has empty version", record.name) });
    }
    if record.module.trim().is_empty() {
        return Err(RlabError::Registry { message: format!("record {} has empty module", record.name) });
    }
    if record.qualname.trim().is_empty() {
        return Err(RlabError::Registry { message: format!("record {} has empty qualname", record.name) });
    }
    Ok(())
}
