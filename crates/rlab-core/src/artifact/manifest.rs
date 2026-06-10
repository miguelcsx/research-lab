use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

pub const ARTIFACT_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactReference {
    pub kind: String,
    pub name: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactManifest {
    pub schema_version: u32,
    pub reference: ArtifactReference,
    pub sha256: String,
    pub object_path: PathBuf,
    pub source_path: PathBuf,
    pub alias: Option<String>,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}
