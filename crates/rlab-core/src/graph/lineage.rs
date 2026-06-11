use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::RlabResult;
use crate::journal::append::{append_jsonl, read_jsonl};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LineageEdge {
    pub schema_version: u32,
    pub from: String,
    pub to: String,
    pub reason: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LineageReport {
    pub schema_version: u32,
    pub reference: String,
    pub upstream: Vec<String>,
    pub downstream: Vec<String>,
}

pub fn add_lineage_edge(
    paths: &ProjectPaths,
    from: &str,
    to: &str,
    reason: Option<String>,
) -> RlabResult<LineageEdge> {
    let edge = LineageEdge {
        schema_version: SCHEMA_VERSION,
        from: from.to_string(),
        to: to.to_string(),
        reason,
    };
    append_jsonl(&paths.cache.join("lineage.jsonl"), &edge)?;
    Ok(edge)
}

pub fn lineage_for(paths: &ProjectPaths, reference: &str) -> RlabResult<LineageReport> {
    let edges: Vec<LineageEdge> = read_jsonl(&paths.cache.join("lineage.jsonl"))?;
    let upstream = edges
        .iter()
        .filter(|edge| edge.to == reference)
        .map(|edge| edge.from.clone())
        .collect();
    let downstream = edges
        .iter()
        .filter(|edge| edge.from == reference)
        .map(|edge| edge.to.clone())
        .collect();
    Ok(LineageReport {
        schema_version: SCHEMA_VERSION,
        reference: reference.to_string(),
        upstream,
        downstream,
    })
}
