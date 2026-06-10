use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::RlabResult;

use super::append::{append_jsonl, read_jsonl};

pub const DECISION_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionEntry {
    pub schema_version: u32,
    pub text: String,
    pub selected_run: Option<String>,
    pub criteria: Value,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

pub fn add_decision(paths: &ProjectPaths, text: &str, selected_run: Option<String>, criteria: Value) -> RlabResult<DecisionEntry> {
    let entry = DecisionEntry {
        schema_version: DECISION_SCHEMA_VERSION,
        text: text.to_string(),
        selected_run,
        criteria,
        created_at: OffsetDateTime::now_utc(),
    };
    append_jsonl(&paths.cache.join("decisions.jsonl"), &entry)?;
    Ok(entry)
}

pub fn list_decisions(paths: &ProjectPaths) -> RlabResult<Vec<DecisionEntry>> {
    read_jsonl(&paths.cache.join("decisions.jsonl"))
}
