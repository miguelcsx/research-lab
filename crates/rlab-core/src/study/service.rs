use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

use super::model::Study;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StudyExecutionPlan {
    pub schema_version: u32,
    pub study: String,
    pub experiment_refs: Vec<String>,
    pub outcome_metrics: Vec<String>,
}

pub fn plan_study(study: &Study) -> RlabResult<StudyExecutionPlan> {
    if study.schema_version != 1 || study.plan.schema_version != 1 {
        return Err(RlabError::Validation {
            message: "unsupported study schema version".to_string(),
        });
    }
    if study.name.trim().is_empty() {
        return Err(RlabError::Validation {
            message: "study name cannot be empty".to_string(),
        });
    }
    if study.plan.experiments.is_empty() {
        return Err(RlabError::Validation {
            message: format!(
                "study {} must reference at least one experiment",
                study.name
            ),
        });
    }
    let outcome_metrics = study
        .plan
        .outcomes
        .iter()
        .map(|outcome| outcome.metric.clone())
        .collect();
    Ok(StudyExecutionPlan {
        schema_version: SCHEMA_VERSION,
        study: study.name.clone(),
        experiment_refs: study.plan.experiments.clone(),
        outcome_metrics,
    })
}
