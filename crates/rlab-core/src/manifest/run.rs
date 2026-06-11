use serde::{Deserialize, Serialize};

pub const RUN_MANIFEST_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunManifestHeader {
    pub schema_version: u32,
    pub kind: String,
}

impl RunManifestHeader {
    pub fn run() -> Self {
        Self {
            schema_version: RUN_MANIFEST_SCHEMA_VERSION,
            kind: "run_manifest".to_string(),
        }
    }
}
