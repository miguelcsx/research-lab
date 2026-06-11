use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::directory::RunDirectory;
use super::{RunId, RunStatus};

const RUN_METADATA_FILE: &str = "run.json";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunSummary {
    pub id: String,
    pub operation: String,
    pub name: String,
    pub status: RunStatus,
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunDetails {
    pub run: RunDirectory,
    pub metrics: Value,
    pub results: Value,
    pub artifacts: Vec<Value>,
    pub logs: Vec<Value>,
    pub error: Option<String>,
}

pub fn list_runs(paths: &ProjectPaths) -> RlabResult<Vec<RunSummary>> {
    if !paths.runs.exists() {
        return Ok(Vec::new());
    }

    let mut runs = read_run_summaries(&paths.runs)?;
    sort_runs_newest_first(&mut runs);

    Ok(runs)
}

pub fn show_run(paths: &ProjectPaths, id: &str) -> RlabResult<RunDirectory> {
    let run_id = RunId::parse(id.to_owned())?;
    read_run(&run_path(paths, run_id.as_str()))
}

pub fn inspect_run(paths: &ProjectPaths, id: &str) -> RlabResult<RunDetails> {
    let run = show_run(paths, id)?;
    Ok(RunDetails {
        metrics: read_json_or_default(
            &run.path.join("metrics_summary.json"),
            Value::Object(Default::default()),
        )?,
        results: read_json_or_default(&run.path.join("results.json"), Value::Null)?,
        artifacts: read_json_lines(&run.path.join("artifacts").join("artifacts.jsonl"))?,
        logs: read_json_lines(&run.path.join("logs").join("events.jsonl"))?,
        error: read_optional_text(&run.path.join("logs").join("error.txt"))?,
        run,
    })
}

fn read_run_summaries(runs_dir: &Path) -> RlabResult<Vec<RunSummary>> {
    let mut runs = Vec::new();

    for entry in read_dir_entries(runs_dir)? {
        let entry = entry.map_err(|error| RlabError::io(runs_dir, error))?;
        let path = entry.path();

        if !path.is_dir() {
            continue;
        }

        if let Some(summary) = read_run_summary_if_valid(&path) {
            runs.push(summary);
        }
    }

    Ok(runs)
}

fn read_dir_entries(path: &Path) -> RlabResult<fs::ReadDir> {
    fs::read_dir(path).map_err(|error| RlabError::io(path, error))
}

fn read_run_summary_if_valid(path: &Path) -> Option<RunSummary> {
    match read_run(path) {
        Ok(run) => Some(run_summary(run, path)),
        Err(_) => None,
    }
}

fn run_summary(run: RunDirectory, path: &Path) -> RunSummary {
    RunSummary {
        id: run.id.as_str().to_owned(),
        operation: run.operation,
        name: run.name,
        status: run.status,
        path: path.display().to_string(),
    }
}

fn sort_runs_newest_first(runs: &mut [RunSummary]) {
    runs.sort_by(|left, right| right.id.cmp(&left.id));
}

fn run_path(paths: &ProjectPaths, run_id: &str) -> PathBuf {
    paths.runs.join(run_id)
}

fn read_run(path: &Path) -> RlabResult<RunDirectory> {
    read_run_file(&run_metadata_path(path))
}

fn run_metadata_path(path: &Path) -> PathBuf {
    path.join(RUN_METADATA_FILE)
}

fn read_run_file(path: &Path) -> RlabResult<RunDirectory> {
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    serde_json::from_str(&content).map_err(RlabError::serialization)
}

fn read_json_or_default(path: &Path, default: Value) -> RlabResult<Value> {
    if !path.exists() {
        return Ok(default);
    }
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    serde_json::from_str(&content).map_err(RlabError::serialization)
}

fn read_json_lines(path: &Path) -> RlabResult<Vec<Value>> {
    if !path.exists() {
        return Ok(Vec::new());
    }
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    content
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).map_err(RlabError::serialization))
        .collect()
}

fn read_optional_text(path: &Path) -> RlabResult<Option<String>> {
    if !path.exists() {
        return Ok(None);
    }
    fs::read_to_string(path)
        .map(Some)
        .map_err(|error| RlabError::io(path, error))
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use serde_json::json;

    use crate::run::RunSession;

    use super::*;

    #[test]
    fn inspect_run_loads_durable_contents() {
        let root = temp_root("inspect");
        let paths = ProjectPaths {
            root: root.clone(),
            runs: root.join(".rlab/runs"),
            artifacts: root.join(".rlab/artifacts"),
            cache: root.join(".rlab/cache"),
            registry_cache: root.join(".rlab/cache/registry.json"),
        };
        let session = RunSession::create(
            &paths,
            "evaluation",
            "quick",
            vec!["rlab".to_string()],
            json!({}),
        )
        .unwrap();
        let id = session.directory.id.as_str().to_string();
        session
            .append_metric(&crate::result::Metric {
                schema_version: 1,
                name: "score".to_string(),
                value: 0.75,
                unit: None,
                direction: None,
                timestamp: time::OffsetDateTime::now_utc(),
            })
            .unwrap();
        session.complete(json!({"data": {"score": 0.75}})).unwrap();

        let details = inspect_run(&paths, &id).unwrap();
        assert_eq!(details.metrics["score"], 0.75);
        assert_eq!(details.results["data"]["score"], 0.75);
        assert_eq!(details.error, None);
        fs::remove_dir_all(root).unwrap();
    }

    fn temp_root(label: &str) -> PathBuf {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        std::env::temp_dir().join(format!("rlab-{label}-{nonce}"))
    }
}
