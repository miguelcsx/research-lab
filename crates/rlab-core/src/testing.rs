use std::fs;
use std::path::Path;

use serde_json::Value;

use crate::error::{RlabError, RlabResult};

const RUN_MANIFEST_FILE: &str = "run.json";
const STATUS_FILE: &str = "status.txt";
const PARAMS_FILE: &str = "params.json";
const METRICS_SUMMARY_FILE: &str = "metrics_summary.json";

pub fn assert_valid_run_dir(path: &Path) -> RlabResult<()> {
    let missing = [RUN_MANIFEST_FILE, STATUS_FILE, PARAMS_FILE]
        .into_iter()
        .filter(|name| !path.join(name).exists())
        .collect::<Vec<_>>();
    if missing.is_empty() {
        return Ok(());
    }

    Err(RlabError::Validation {
        message: format!("invalid run directory; missing {missing:?}"),
    })
}

pub fn assert_metric_exists(path: &Path, name: &str) -> RlabResult<()> {
    let metrics_path = path.join(METRICS_SUMMARY_FILE);
    if !metrics_path.exists() {
        return Err(RlabError::NotFound {
            subject: METRICS_SUMMARY_FILE.to_string(),
        });
    }
    let content =
        fs::read_to_string(&metrics_path).map_err(|error| RlabError::io(&metrics_path, error))?;
    let values: Value = serde_json::from_str(&content).map_err(RlabError::serialization)?;
    if values.get(name).is_some() {
        return Ok(());
    }

    Err(RlabError::Validation {
        message: format!("metric {name:?} does not exist"),
    })
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    #[test]
    fn validates_run_dir_and_metrics() {
        let root = temp_root("valid");
        fs::create_dir_all(&root).expect("create temp root");
        fs::write(root.join(RUN_MANIFEST_FILE), "{}").expect("manifest");
        fs::write(root.join(STATUS_FILE), "completed").expect("status");
        fs::write(root.join(PARAMS_FILE), "{}").expect("params");
        fs::write(root.join(METRICS_SUMMARY_FILE), r#"{"accuracy":0.9}"#).expect("metrics");

        assert!(assert_valid_run_dir(&root).is_ok());
        assert!(assert_metric_exists(&root, "accuracy").is_ok());
        assert!(assert_metric_exists(&root, "loss").is_err());

        cleanup(root);
    }

    fn temp_root(label: &str) -> std::path::PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_nanos())
            .unwrap_or_default();
        std::env::temp_dir().join(format!("rlab-testing-{label}-{unique}"))
    }

    fn cleanup(root: std::path::PathBuf) {
        if root.exists() {
            fs::remove_dir_all(root).expect("cleanup");
        }
    }
}
