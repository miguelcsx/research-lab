use std::collections::BTreeMap;
use std::fs;
use std::io::{BufRead, BufReader};
use std::path::Path;

use crate::error::{RlabError, RlabResult};
use crate::fs::write_json_atomic;
use crate::result::Metric;

pub const RUN_MANIFEST_FILE: &str = "run.json";
pub const RUN_MANIFEST_YAML_FILE: &str = "run.yaml";
pub const STATUS_FILE: &str = "status.txt";
pub const PARAMS_FILE: &str = "params.json";
pub const METRICS_FILE: &str = "metrics.jsonl";
pub const METRICS_SUMMARY_FILE: &str = "metrics_summary.json";
pub const RESULTS_FILE: &str = "results.json";
pub const NOTES_FILE: &str = "notes.jsonl";
pub const EVENTS_FILE: &str = "events.jsonl";
pub const ARTIFACTS_FILE: &str = "artifacts.jsonl";
pub const ERROR_FILE: &str = "error.txt";

pub const RUN_DIR_LOGS: &str = "logs";
pub const RUN_DIR_ARTIFACTS: &str = "artifacts";
pub const RUN_DIR_TABLES: &str = "tables";
pub const RUN_DIR_FIGURES: &str = "figures";
pub const RUN_DIR_RESULTS: &str = "results";
pub const RUN_DIR_EXTERNAL: &str = "external";
pub const RUN_DIR_REPRODUCIBILITY: &str = "reproducibility";

pub fn read_metrics(run_dir: &Path) -> RlabResult<Vec<Metric>> {
    let path = run_dir.join(METRICS_FILE);

    if !path.exists() {
        return Ok(Vec::new());
    }

    let file = fs::File::open(&path).map_err(|error| RlabError::io(&path, error))?;
    let reader = BufReader::new(file);
    let mut metrics = Vec::new();

    for line in reader.lines() {
        let line = line.map_err(|error| RlabError::io(&path, error))?;

        if line.trim().is_empty() {
            continue;
        }

        metrics.push(serde_json::from_str::<Metric>(&line).map_err(RlabError::serialization)?);
    }

    Ok(metrics)
}

pub fn write_metric_summary(run_dir: &Path) -> RlabResult<BTreeMap<String, f64>> {
    let mut summary = BTreeMap::new();

    for metric in read_metrics(run_dir)? {
        summary.insert(metric.name, metric.value);
    }

    write_json_atomic(&run_dir.join(METRICS_SUMMARY_FILE), &summary)?;

    Ok(summary)
}
