use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub struct RegistryName(String);

impl RegistryName {
    pub fn parse(value: &str) -> RlabResult<Self> {
        if value.is_empty() {
            return Err(RlabError::Registry { message: "registry name cannot be empty".to_string() });
        }
        if value.chars().any(char::is_whitespace) {
            return Err(RlabError::Registry { message: format!("registry name contains whitespace: {value}") });
        }
        let valid = value
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '.' | '_' | '-' | ':'));
        if !valid {
            return Err(RlabError::Registry { message: format!("registry name contains invalid characters: {value}") });
        }
        Ok(Self(value.to_string()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}
