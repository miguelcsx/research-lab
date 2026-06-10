use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
use crate::result::Metric;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkSpec {
    pub schema_version: u32,
    pub name: String,
    pub target_kind: String,
    pub params: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkContext {
    pub schema_version: u32,
    pub benchmark: String,
    pub target: String,
    pub data: Option<String>,
    pub params: BTreeMap<String, Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BenchmarkResult {
    pub schema_version: u32,
    pub benchmark: String,
    pub target: String,
    pub metrics: Vec<Metric>,
}

impl BenchmarkSpec {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported benchmark schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() || self.target_kind.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "benchmark name and target_kind are required".to_string(),
            });
        }
        Ok(())
    }
}

impl BenchmarkResult {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported benchmark result schema_version".to_string(),
            });
        }
        for metric in &self.metrics {
            metric.validate()?;
        }
        Ok(())
    }
}
