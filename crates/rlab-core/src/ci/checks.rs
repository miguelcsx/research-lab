use serde::{Deserialize, Serialize};

use crate::compare::compare_runs;
use crate::config::{EffectiveConfig, ProjectPaths};
use crate::diagnostic::doctor_project;
use crate::error::{RlabError, RlabResult};
use crate::run::list_runs;

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CiCheckResult {
    pub schema_version: u32,
    pub passed: bool,
    pub message: String,
}

pub fn ci_smoke(config: &EffectiveConfig, paths: &ProjectPaths) -> RlabResult<CiCheckResult> {
    let findings = doctor_project(config, paths)?;
    let failed = findings
        .iter()
        .any(|finding| finding.level.as_str() == "error");
    Ok(CiCheckResult {
        schema_version: SCHEMA_VERSION,
        passed: !failed,
        message: format!("{} diagnostics checked", findings.len()),
    })
}

pub fn ci_compare(paths: &ProjectPaths, metric: &str, threshold: f64) -> RlabResult<CiCheckResult> {
    let rows = compare_runs(paths, Some(metric.to_string()))?;
    let values = rows
        .into_iter()
        .filter_map(|row| row.metrics.get(metric).copied())
        .collect::<Vec<_>>();
    if values.len() < 2 {
        return Err(RlabError::Validation {
            message: "ci compare requires at least two runs with the selected metric".to_string(),
        });
    }
    let first = values[0];
    let last = values[values.len() - 1];
    let delta = (last - first).abs();
    Ok(CiCheckResult {
        schema_version: SCHEMA_VERSION,
        passed: delta <= threshold,
        message: format!("metric {metric} delta {delta} threshold {threshold}"),
    })
}

pub fn ci_reproducibility_check(paths: &ProjectPaths) -> RlabResult<CiCheckResult> {
    let missing = list_runs(paths)?
        .into_iter()
        .filter(|run| {
            !paths
                .runs
                .join(&run.id)
                .join("reproducibility/env.json")
                .exists()
        })
        .map(|run| run.id)
        .collect::<Vec<_>>();
    Ok(CiCheckResult {
        schema_version: SCHEMA_VERSION,
        passed: missing.is_empty(),
        message: format!(
            "runs missing reproducibility metadata: {}",
            missing.join(",")
        ),
    })
}
