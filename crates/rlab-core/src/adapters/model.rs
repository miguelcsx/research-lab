use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AdapterCapability {
    ExternalCommand,
    ExternalEvaluation,
    RepositoryCheckout,
    ArtifactMapping,
    CustomParser,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum AdapterStatus {
    Declared,
    Importable,
    MissingSource,
    Invalid,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterDescriptor {
    pub schema_version: u32,
    pub name: String,
    pub module: String,
    pub qualname: String,
    pub source: PathBuf,
    pub capabilities: Vec<AdapterCapability>,
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AdapterHealth {
    pub schema_version: u32,
    pub descriptor: AdapterDescriptor,
    pub status: AdapterStatus,
    pub findings: Vec<String>,
}
