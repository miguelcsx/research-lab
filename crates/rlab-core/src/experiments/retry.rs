use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum FailureKind {
    Timeout,
    ResourceError,
    PythonException,
    ExternalCommand,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetryPolicy {
    pub schema_version: u32,
    pub max_attempts: u32,
    pub on: Vec<FailureKind>,
    pub delay_seconds: f64,
}

impl RetryPolicy {
    pub fn none() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            max_attempts: 1,
            on: Vec::new(),
            delay_seconds: 0.0,
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported retry policy schema_version".to_string(),
            });
        }
        if self.max_attempts == 0 {
            return Err(RlabError::Validation {
                message: "retry max_attempts must be at least 1".to_string(),
            });
        }
        if !self.delay_seconds.is_finite() || self.delay_seconds < 0.0 {
            return Err(RlabError::Validation {
                message: "retry delay_seconds must be finite and non-negative".to_string(),
            });
        }
        Ok(())
    }
}
