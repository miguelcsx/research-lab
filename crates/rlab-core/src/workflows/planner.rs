use serde::{Deserialize, Serialize};

use crate::error::RlabResult;

use super::model::{Workflow, WorkflowStep};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowPlan {
    pub schema_version: u32,
    pub workflow: String,
    pub steps: Vec<WorkflowStep>,
}

pub fn plan_workflow(workflow: &Workflow) -> RlabResult<WorkflowPlan> {
    workflow.validate()?;
    Ok(WorkflowPlan {
        schema_version: SCHEMA_VERSION,
        workflow: workflow.name.clone(),
        steps: workflow.steps.clone(),
    })
}
