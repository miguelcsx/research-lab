use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use super::protocol::ProtocolVersion;
use crate::registry::RegistryKind;

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum HostCommand {
    Discover,
    ValidateImports,
    Execute,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostTarget {
    pub kind: RegistryKind,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HostRequest {
    pub protocol_version: ProtocolVersion,
    pub request_id: String,
    pub command: HostCommand,
    pub project_root: PathBuf,
    pub modules: Vec<String>,
    pub target: Option<HostTarget>,
    pub run_id: Option<String>,
    pub params: Value,
    pub seed: Option<u64>,
    pub strict: bool,
    pub environment: Value,
}
