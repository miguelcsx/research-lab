use serde::{Deserialize, Serialize};

use super::event::HostEvent;
use super::protocol::ProtocolVersion;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostResponse {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub events: Vec<HostEvent>,
}
