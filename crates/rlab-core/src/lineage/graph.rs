use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::RlabResult;
use crate::graph::lineage_for;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LineageImpact {
    pub schema_version: u32,
    pub reference: String,
    pub direct_upstream: Vec<String>,
    pub direct_downstream: Vec<String>,
    pub affected_count: usize,
}

pub fn impact_report(paths: &ProjectPaths, reference: &str) -> RlabResult<LineageImpact> {
    let report = lineage_for(paths, reference)?;
    let affected_count = report.downstream.len();
    Ok(LineageImpact {
        schema_version: SCHEMA_VERSION,
        reference: report.reference,
        direct_upstream: report.upstream,
        direct_downstream: report.downstream,
        affected_count,
    })
}
