use serde::{Deserialize, Serialize};
use serde_json::Value;
use time::OffsetDateTime;

pub const RUN_EVENT_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunEvent {
    pub schema_version: u32,
    pub event_type: String,
    #[serde(with = "time::serde::rfc3339")]
    pub timestamp: OffsetDateTime,
    pub payload: Value,
}

impl RunEvent {
    pub fn new(event_type: String, payload: Value) -> Self {
        Self {
            schema_version: RUN_EVENT_SCHEMA_VERSION,
            event_type,
            timestamp: OffsetDateTime::now_utc(),
            payload,
        }
    }
}
