use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Workflow {
    pub schema_version: u32,
    pub name: String,
    pub steps: Vec<WorkflowStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    pub schema_version: u32,
    pub name: String,
    pub kind: WorkflowStepKind,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum WorkflowStepKind {
    Python { module: String, qualname: String },
    External(ExternalStep),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExternalStep {
    pub schema_version: u32,
    pub command: Vec<String>,
    pub cwd: Option<String>,
    pub timeout_seconds: u64,
}

impl Workflow {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation { message: "unsupported workflow schema_version".to_string() });
        }
        if self.name.trim().is_empty() {
            return Err(RlabError::Validation { message: "workflow name cannot be empty".to_string() });
        }
        if self.steps.is_empty() {
            return Err(RlabError::Validation { message: format!("workflow {} has no steps", self.name) });
        }
        for step in &self.steps {
            step.validate()?;
        }
        Ok(())
    }
}

impl WorkflowStep {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation { message: "unsupported workflow step schema_version".to_string() });
        }
        if self.name.trim().is_empty() {
            return Err(RlabError::Validation { message: "workflow step name cannot be empty".to_string() });
        }
        match &self.kind {
            WorkflowStepKind::Python { module, qualname } => {
                if module.trim().is_empty() || qualname.trim().is_empty() {
                    return Err(RlabError::Validation { message: "python workflow step requires module and qualname".to_string() });
                }
            }
            WorkflowStepKind::External(step) => step.validate()?,
        }
        Ok(())
    }
}

impl ExternalStep {
    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != 1 {
            return Err(RlabError::Validation { message: "unsupported external step schema_version".to_string() });
        }
        if self.command.is_empty() || self.command.iter().any(|part| part.trim().is_empty()) {
            return Err(RlabError::Validation { message: "external step command cannot be empty".to_string() });
        }
        if self.timeout_seconds == 0 {
            return Err(RlabError::Validation { message: "external step timeout_seconds must be greater than zero".to_string() });
        }
        Ok(())
    }
}
