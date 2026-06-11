use serde::{Deserialize, Serialize};

pub const CURRENT_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SchemaVersion {
    pub schema_version: u32,
    pub kind: String,
}

impl SchemaVersion {
    pub fn current(kind: &str) -> Self {
        Self {
            schema_version: CURRENT_SCHEMA_VERSION,
            kind: kind.to_string(),
        }
    }
}
