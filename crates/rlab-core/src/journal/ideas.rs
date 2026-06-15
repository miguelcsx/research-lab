use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::write_json_atomic;

use super::append::{append_jsonl, read_jsonl};

pub const IDEA_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum IdeaStatus {
    Idea,
    Planned,
    Running,
    Validated,
    Rejected,
    Published,
}

impl IdeaStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Idea => "idea",
            Self::Planned => "planned",
            Self::Running => "running",
            Self::Validated => "validated",
            Self::Rejected => "rejected",
            Self::Published => "published",
        }
    }

    pub fn parse(value: &str) -> RlabResult<Self> {
        match value {
            "idea" => Ok(Self::Idea),
            "planned" => Ok(Self::Planned),
            "running" => Ok(Self::Running),
            "validated" => Ok(Self::Validated),
            "rejected" => Ok(Self::Rejected),
            "published" => Ok(Self::Published),
            _ => Err(RlabError::Validation {
                message: format!("invalid idea status: {value}"),
            }),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IdeaEntry {
    pub schema_version: u32,
    pub id: String,
    pub text: String,
    pub status: IdeaStatus,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

impl IdeaEntry {
    pub fn new(text: String, status: IdeaStatus) -> Self {
        Self {
            schema_version: IDEA_SCHEMA_VERSION,
            id: format!("idea_{}", OffsetDateTime::now_utc().unix_timestamp_nanos()),
            text,
            status,
            created_at: OffsetDateTime::now_utc(),
        }
    }
}

pub fn add_idea(paths: &ProjectPaths, text: &str) -> RlabResult<IdeaEntry> {
    let entry = IdeaEntry::new(text.to_string(), IdeaStatus::Idea);
    append_jsonl(&paths.cache.join("ideas.jsonl"), &entry)?;
    Ok(entry)
}

pub fn list_ideas(paths: &ProjectPaths) -> RlabResult<Vec<IdeaEntry>> {
    read_jsonl(&paths.cache.join("ideas.jsonl"))
}

pub fn promote_idea(
    paths: &ProjectPaths,
    id: &str,
    status: IdeaStatus,
) -> RlabResult<Vec<IdeaEntry>> {
    let entries = list_ideas(paths)?
        .into_iter()
        .map(|mut entry| {
            if entry.id == id {
                entry.status = status;
            }
            entry
        })
        .collect::<Vec<_>>();
    let snapshot = paths.cache.join("ideas.snapshot.json");
    write_json_atomic(&snapshot, &entries)?;
    Ok(entries)
}
