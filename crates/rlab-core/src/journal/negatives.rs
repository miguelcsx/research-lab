use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::RlabResult;

use super::append::{append_jsonl, read_jsonl};

pub const NEGATIVE_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NegativeResultEntry {
    pub schema_version: u32,
    pub hypothesis: String,
    pub tried: String,
    pub reason: String,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

impl NegativeResultEntry {
    pub fn new(hypothesis: String, tried: String, reason: String) -> Self {
        Self {
            schema_version: NEGATIVE_SCHEMA_VERSION,
            hypothesis,
            tried,
            reason,
            created_at: OffsetDateTime::now_utc(),
        }
    }
}

pub fn add_negative_result(
    paths: &ProjectPaths,
    hypothesis: &str,
    tried: &str,
    reason: &str,
) -> RlabResult<NegativeResultEntry> {
    let entry = NegativeResultEntry::new(
        hypothesis.to_string(),
        tried.to_string(),
        reason.to_string(),
    );
    append_jsonl(&paths.cache.join("negatives.jsonl"), &entry)?;
    Ok(entry)
}

pub fn list_negative_results(paths: &ProjectPaths) -> RlabResult<Vec<NegativeResultEntry>> {
    read_jsonl(&paths.cache.join("negatives.jsonl"))
}

pub fn search_negative_results(
    paths: &ProjectPaths,
    term: &str,
) -> RlabResult<Vec<NegativeResultEntry>> {
    let needle = term.to_lowercase();
    Ok(list_negative_results(paths)?
        .into_iter()
        .filter(|entry| {
            entry.hypothesis.to_lowercase().contains(&needle)
                || entry.tried.to_lowercase().contains(&needle)
                || entry.reason.to_lowercase().contains(&needle)
        })
        .collect())
}
