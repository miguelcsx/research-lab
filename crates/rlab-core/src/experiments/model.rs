use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::retry::RetryPolicy;

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExperimentSpec {
    pub schema_version: u32,
    pub name: String,
    pub question: Option<String>,
    pub hypothesis: Option<String>,
    pub params: BTreeMap<String, Value>,
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
        validate_schema_version(self.schema_version)?;
        validate_name(&self.name)?;
        validate_metrics(&self.metrics)?;
        self.retry.validate()
    }
}

fn validate_schema_version(schema_version: u32) -> RlabResult<()> {
    if schema_version == SCHEMA_VERSION {
        return Ok(());
    }

    Err(RlabError::validation(
        "unsupported experiment schema_version",
    ))
}

fn validate_name(name: &str) -> RlabResult<()> {
    if !name.trim().is_empty() {
        return Ok(());
    }

    Err(RlabError::validation("experiment name cannot be empty"))
}

fn validate_metrics(metrics: &[String]) -> RlabResult<()> {
    for metric in metrics {
        if metric.trim().is_empty() {
            return Err(RlabError::validation("metric names cannot be empty"));
        }
    }

    Ok(())
}
