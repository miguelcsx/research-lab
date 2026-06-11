use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::retry::RetryPolicy;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSpec {
    pub schema_version: u32,
    pub name: String,
    pub question: Option<String>,
    pub hypothesis: Option<String>,
    pub matrix: BTreeMap<String, Vec<Value>>,
    pub metrics: Vec<String>,
    pub seeds: Vec<u64>,
    pub retry: RetryPolicy,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentJob {
    pub schema_version: u32,
    pub job_id: String,
    pub experiment: String,
    pub params: BTreeMap<String, Value>,
    pub seed: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentPlan {
    pub schema_version: u32,
    pub experiment: String,
    pub jobs: Vec<ExperimentJob>,
}

impl ExperimentSpec {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported experiment schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "experiment name cannot be empty".to_string(),
            });
        }
        for metric in &self.metrics {
            if metric.trim().is_empty() {
                return Err(RlabError::Validation {
                    message: "metric names cannot be empty".to_string(),
                });
            }
        }
        self.retry.validate()
    }
}
