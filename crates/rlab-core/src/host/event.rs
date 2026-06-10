use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::registry::RegistryRecord;
use crate::result::Metric;

use super::protocol::ProtocolVersion;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event_type", rename_all = "snake_case")]
pub enum HostEvent {
    RegistryRecord(RegistryEvent),
    Metric(MetricEvent),
    Artifact(ArtifactEvent),
    Log(LogEvent),
    Warning(LogEvent),
    Error(LogEvent),
    Completed { protocol_version: ProtocolVersion, request_id: String, result: Value },
    Failed { protocol_version: ProtocolVersion, request_id: String, error: Value },
    Batch { protocol_version: ProtocolVersion, request_id: String, events: Vec<HostEvent> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistryEvent {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub record: RegistryRecord,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricEvent {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub metric: Metric,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactEvent {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub artifact: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEvent {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub message: String,
}
