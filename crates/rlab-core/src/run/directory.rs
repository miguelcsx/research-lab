use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;

use crate::error::{RlabError, RlabResult};

use super::{RunId, RunStatus};

pub const RUN_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunDirectory {
    pub schema_version: u32,
    pub id: RunId,
    pub operation: String,
    pub name: String,
    pub status: RunStatus,
    pub path: PathBuf,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
    #[serde(with = "time::serde::rfc3339")]
    pub updated_at: OffsetDateTime,
    pub command: Vec<String>,
    pub parameters: Value,
    pub notes: Option<String>,
}

impl RunDirectory {
    pub fn validate_schema(&self) -> RlabResult<()> {
        if self.schema_version != RUN_SCHEMA_VERSION {
            return Err(RlabError::Run {
                message: format!("unsupported run schema version: {}", self.schema_version),
            });
        }
        Ok(())
    }
}
