use serde::{Deserialize, Serialize};

pub const ARTIFACT_MANIFEST_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactManifestHeader {
    pub schema_version: u32,
    pub kind: String,
}

impl ArtifactManifestHeader {
    pub fn artifact() -> Self {
        Self {
            schema_version: ARTIFACT_MANIFEST_SCHEMA_VERSION,
            kind: "artifact_manifest".to_string(),
        }
    }
}
