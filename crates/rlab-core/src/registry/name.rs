use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct RegistryName(String);

impl RegistryName {
    pub fn parse(value: &str) -> RlabResult<Self> {
        validate_registry_name(value)?;

        Ok(Self(value.to_string()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn validate_registry_name(value: &str) -> RlabResult<()> {
    if value.is_empty() {
        return Err(RlabError::registry("registry name cannot be empty"));
    }

    if value.chars().any(char::is_whitespace) {
        return Err(RlabError::registry(format!(
            "registry name contains whitespace: {value}"
        )));
    }

    if !value.chars().all(is_valid_registry_name_character) {
        return Err(RlabError::registry(format!(
            "registry name contains invalid characters: {value}"
        )));
    }

    Ok(())
}

fn is_valid_registry_name_character(character: char) -> bool {
    character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-' | ':')
}
