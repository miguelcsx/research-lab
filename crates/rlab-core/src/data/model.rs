use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ComponentUse {
    pub schema_version: u32,
    pub reference: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "decision", rename_all = "snake_case")]
pub enum DataDecision {
    Keep {
        schema_version: u32,
        record: Value,
    },
    Update {
        schema_version: u32,
        record: Value,
        reason: Option<String>,
    },
    Drop {
        schema_version: u32,
        reason: String,
    },
    Boundary {
        schema_version: u32,
        value: Value,
        kind: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataBoundary {
    pub schema_version: u32,
    pub value: Value,
    pub kind: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PipelineSpec {
    pub schema_version: u32,
    pub name: String,
    pub stages: Vec<ComponentUse>,
    pub version: String,
    pub tags: Vec<String>,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatasetSpec {
    pub schema_version: u32,
    pub name: String,
    pub source: ComponentUse,
    pub pipeline: String,
    pub sinks: Vec<ComponentUse>,
    pub checks: Vec<ComponentUse>,
    pub metrics: Vec<ComponentUse>,
    pub audit: AuditPolicy,
    pub version: String,
    pub tags: Vec<String>,
    pub description: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuditPolicy {
    pub schema_version: u32,
    pub capture_decisions: bool,
    pub sample_limit_per_reason: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataDocument {
    pub dataset: DataDocumentDataset,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DataDocumentDataset {
    pub name: String,
    pub description: Option<String>,
    pub tags: Option<Vec<String>>,
}

impl ComponentUse {
    pub fn new(reference: String) -> RlabResult<Self> {
        if reference.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "component reference cannot be empty".to_string(),
            });
        }
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            reference,
        })
    }
}

impl PipelineSpec {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported pipeline schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() || self.version.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "pipeline name and version are required".to_string(),
            });
        }
        Ok(())
    }
}

impl DatasetSpec {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported dataset schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty()
            || self.version.trim().is_empty()
            || self.pipeline.trim().is_empty()
        {
            return Err(RlabError::Validation {
                message: "dataset name, version, and pipeline are required".to_string(),
            });
        }
        self.audit.validate()
    }
}

impl AuditPolicy {
    pub fn relaxed() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            capture_decisions: false,
            sample_limit_per_reason: 10,
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported audit policy schema_version".to_string(),
            });
        }
        Ok(())
    }
}
