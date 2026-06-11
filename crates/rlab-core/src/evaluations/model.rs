use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};
use crate::result::Metric;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationTask {
    pub schema_version: u32,
    pub suite: String,
    pub name: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationSuite {
    pub schema_version: u32,
    pub name: String,
    pub tasks: Vec<EvaluationTask>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub schema_version: u32,
    pub task: String,
    pub metrics: Vec<Metric>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvaluationResult {
    pub schema_version: u32,
    pub suite: String,
    pub model: String,
    pub tasks: Vec<TaskResult>,
}

impl EvaluationSuite {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported evaluation suite schema_version".to_string(),
            });
        }
        if self.name.trim().is_empty() {
            return Err(RlabError::Validation {
                message: "evaluation suite name cannot be empty".to_string(),
            });
        }
        if self.tasks.is_empty() {
            return Err(RlabError::Validation {
                message: format!("evaluation suite {} has no tasks", self.name),
            });
        }
        Ok(())
    }
}

impl EvaluationResult {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation {
                message: "unsupported evaluation result schema_version".to_string(),
            });
        }
        for task in &self.tasks {
            for metric in &task.metrics {
                metric.validate()?;
            }
        }
        Ok(())
    }
}
