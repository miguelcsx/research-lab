use serde::{Deserialize, Serialize};

pub const CURRENT_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct SchemaVersion(pub u32);

impl SchemaVersion {
    pub fn current() -> Self {
        Self(CURRENT_SCHEMA_VERSION)
    }
}
