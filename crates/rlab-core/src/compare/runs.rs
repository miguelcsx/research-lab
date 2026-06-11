use std::collections::BTreeMap;
use std::fs;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::run::list_runs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompareRow {
    pub run_id: String,
    pub metrics: BTreeMap<String, f64>,
}

pub fn compare_runs(
    paths: &ProjectPaths,
    metric_filter: Option<String>,
) -> RlabResult<Vec<CompareRow>> {
    let runs = list_runs(paths)?;
    let mut rows = Vec::new();
    for run in runs {
        let path = paths.runs.join(&run.id).join("metrics_summary.json");
        if path.exists() {
            let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
            let mut metrics = parse_metric_summary(&content)?;
            if let Some(metric) = &metric_filter {
                metrics.retain(|name, _| name == metric);
            }
            if metric_filter.is_none() || !metrics.is_empty() {
                rows.push(CompareRow {
                    run_id: run.id,
                    metrics,
                });
            }
        }
    }
    Ok(rows)
}

fn parse_metric_summary(content: &str) -> RlabResult<BTreeMap<String, f64>> {
    let value: Value = serde_json::from_str(content).map_err(RlabError::serialization)?;
    if let Some(metrics) = value.get("metrics") {
        return parse_metrics_object(metrics);
    }
    parse_metrics_object(&value)
}

fn parse_metrics_object(value: &Value) -> RlabResult<BTreeMap<String, f64>> {
    let object = value.as_object().ok_or_else(|| RlabError::Serialization {
        message: "metrics summary must be a JSON object".to_string(),
    })?;
    let mut metrics = BTreeMap::new();
    for (name, metric_value) in object {
        if let Some(number) = metric_value.as_f64() {
            metrics.insert(name.clone(), number);
        }
    }
    Ok(metrics)
}
