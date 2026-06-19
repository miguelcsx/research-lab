use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::error::{RlabError, RlabResult};

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

pub fn parse_artifact_name(value: &str) -> RlabResult<(String, String)> {
    let mut split = value.splitn(2, ':');
    let kind = match split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact name: {value}"),
            })
        }
    };
    let name = match split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("artifact name must be kind:name: {value}"),
            })
        }
    };
    Ok((kind, name))
}

pub fn parse_artifact_reference(value: &str) -> RlabResult<ArtifactReference> {
    let without_scheme = value.strip_prefix("artifact:").unwrap_or(value);
    let mut version_split = without_scheme.splitn(2, '@');
    let left = match version_split.next() {
        Some(text) if !text.trim().is_empty() => text,
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact reference: {value}"),
            })
        }
    };
    let version = match version_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => "1".to_string(),
    };
    let mut kind_split = left.splitn(2, '/');
    let kind = match kind_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact reference: {value}"),
            })
        }
    };
    let name = match kind_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("artifact reference must be artifact:kind/name@version: {value}"),
            })
        }
    };
    Ok(ArtifactReference {
        kind,
        name,
        version,
    })
}
