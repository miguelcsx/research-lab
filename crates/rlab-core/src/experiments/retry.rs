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
        validate_schema_version(self.schema_version)?;
        validate_max_attempts(self.max_attempts)?;
        validate_delay_seconds(self.delay_seconds)
    }
}

fn validate_schema_version(schema_version: u32) -> RlabResult<()> {
    if schema_version == SCHEMA_VERSION {
        return Ok(());
    }

    Err(RlabError::validation(
        "unsupported retry policy schema_version",
    ))
}

fn validate_max_attempts(max_attempts: u32) -> RlabResult<()> {
    if max_attempts > 0 {
        return Ok(());
    }

    Err(RlabError::validation(
        "retry max_attempts must be at least 1",
    ))
}

fn validate_delay_seconds(delay_seconds: f64) -> RlabResult<()> {
    if delay_seconds.is_finite() && delay_seconds >= 0.0 {
        return Ok(());
    }

    Err(RlabError::validation(
        "retry delay_seconds must be finite and non-negative",
    ))
}
