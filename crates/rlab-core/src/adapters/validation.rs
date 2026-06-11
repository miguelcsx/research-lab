use crate::error::{RlabError, RlabResult};
use crate::registry::RegistryName;

use super::model::AdapterDescriptor;

pub fn validate_adapter_descriptor(descriptor: &AdapterDescriptor) -> RlabResult<()> {
    if descriptor.schema_version != 1 {
        return Err(RlabError::Validation {
            message: format!(
                "unsupported adapter schema version: {}",
                descriptor.schema_version
            ),
        });
    }
    RegistryName::parse(&descriptor.name)?;
    if descriptor.module.trim().is_empty() {
        return Err(RlabError::Validation {
            message: "adapter module cannot be empty".to_string(),
        });
    }
    if descriptor.qualname.trim().is_empty() {
        return Err(RlabError::Validation {
            message: "adapter qualname cannot be empty".to_string(),
        });
    }
    if descriptor.capabilities.is_empty() {
        return Err(RlabError::Validation {
            message: format!(
                "adapter {} must declare at least one capability",
                descriptor.name
            ),
        });
    }
    Ok(())
}
