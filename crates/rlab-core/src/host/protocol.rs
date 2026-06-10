use serde::{Deserialize, Serialize};

pub const PROTOCOL_VERSION_NUMBER: u32 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct ProtocolVersion(pub u32);

impl ProtocolVersion {
    pub fn current() -> Self {
        Self(PROTOCOL_VERSION_NUMBER)
    }
}
