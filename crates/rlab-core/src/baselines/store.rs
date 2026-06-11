use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::journal::append::{append_jsonl, read_jsonl};
use crate::run::show_run;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BaselineComparison {
    pub schema_version: u32,
    pub name: String,
    pub metric: String,
    pub baseline_value: f64,
    pub run_value: Option<f64>,
    pub delta: Option<f64>,
}

pub fn add_baseline(
    paths: &ProjectPaths,
    name: &str,
    metric: &str,
    value: f64,
    description: Option<String>,
) -> RlabResult<crate::evaluations::BaselineEntry> {
    let entry = crate::evaluations::BaselineEntry {
        schema_version: SCHEMA_VERSION,
        name: name.to_string(),
        metric: metric.to_string(),
        value,
        description,
        created_at: OffsetDateTime::now_utc(),
    };
    append_jsonl(&paths.cache.join("baselines.jsonl"), &entry)?;
    Ok(entry)
}

pub fn list_baselines(paths: &ProjectPaths) -> RlabResult<Vec<crate::evaluations::BaselineEntry>> {
    read_jsonl(&paths.cache.join("baselines.jsonl"))
}

pub fn compare_baseline(paths: &ProjectPaths, run_id: &str) -> RlabResult<Vec<BaselineComparison>> {
    let run = show_run(paths, run_id)?;
    let metrics_path = run.path.join("metrics_summary.json");
    let metrics = if metrics_path.exists() {
        let content = std::fs::read_to_string(&metrics_path)
            .map_err(|error| RlabError::io(&metrics_path, error))?;
        serde_json::from_str::<std::collections::BTreeMap<String, f64>>(&content)
            .map_err(RlabError::serialization)?
    } else {
        std::collections::BTreeMap::new()
    };
    Ok(list_baselines(paths)?
        .into_iter()
        .map(|baseline| {
            let run_value = metrics.get(&baseline.metric).copied();
            let delta = run_value.map(|value| value - baseline.value);
            BaselineComparison {
                schema_version: SCHEMA_VERSION,
                name: baseline.name,
                metric: baseline.metric,
                baseline_value: baseline.value,
                run_value,
                delta,
            }
        })
        .collect())
}
