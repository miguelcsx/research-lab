use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::error::{RlabError, RlabResult};

pub const ARTIFACT_SCHEMA_VERSION: u32 = 2;
pub const TREE_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArtifactReference {
    pub kind: String,
    pub name: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactPathReference {
    pub reference: ArtifactReference,
    pub suffix: Option<PathBuf>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactManifest {
    pub schema_version: u32,
    pub reference: ArtifactReference,
    pub sha256: String,
    pub storage_type: ArtifactStorageType,
    pub object_path: PathBuf,
    pub source_path: PathBuf,
    pub size_bytes: u64,
    pub alias: Option<String>,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ArtifactStorageType {
    File,
    Directory,
}

impl ArtifactStorageType {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::File => "file",
            Self::Directory => "directory",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TreeManifest {
    pub schema_version: u32,
    pub digest: String,
    pub entries: Vec<TreeEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TreeEntry {
    pub path: String,
    pub sha256: String,
    pub size_bytes: u64,
    pub mode: u32,
    pub executable: bool,
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
    Ok(parse_artifact_path_reference(value)?.reference)
}

pub fn parse_artifact_path_reference(value: &str) -> RlabResult<ArtifactPathReference> {
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
    let version_and_suffix = version_split.next().unwrap_or("1");
    let (version, suffix) = match version_and_suffix.split_once('/') {
        Some((version, suffix)) if !version.trim().is_empty() && !suffix.trim().is_empty() => {
            (version.to_string(), Some(PathBuf::from(suffix)))
        }
        Some(_) => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact reference suffix: {value}"),
            })
        }
        None => (version_and_suffix.to_string(), None),
    };
    if version.trim().is_empty() {
        return Err(RlabError::Reference {
            message: format!("invalid artifact version: {value}"),
        });
    }
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
    Ok(ArtifactPathReference {
        reference: ArtifactReference {
            kind,
            name,
            version,
        },
        suffix,
    })
}
