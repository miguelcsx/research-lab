use std::path::Path;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::RlabResult;

use super::append::{append_jsonl, read_jsonl};

pub const NOTE_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteEntry {
    pub schema_version: u32,
    pub run_id: String,
    pub text: String,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

pub fn add_run_note(paths: &ProjectPaths, run_id: &str, text: &str) -> RlabResult<NoteEntry> {
    let entry = NoteEntry {
        schema_version: NOTE_SCHEMA_VERSION,
        run_id: run_id.to_string(),
        text: text.to_string(),
        created_at: OffsetDateTime::now_utc(),
    };
    append_jsonl(&run_notes_path(paths, run_id), &entry)?;
    append_jsonl(&paths.cache.join("notes.jsonl"), &entry)?;
    Ok(entry)
}

pub fn list_run_notes(paths: &ProjectPaths, run_id: &str) -> RlabResult<Vec<NoteEntry>> {
    read_jsonl(&run_notes_path(paths, run_id))
}

fn run_notes_path(paths: &ProjectPaths, run_id: &str) -> std::path::PathBuf {
    Path::new(&paths.runs).join(run_id).join("notes.jsonl")
}
