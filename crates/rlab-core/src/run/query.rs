use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::directory::RunDirectory;
use super::store::{
    ARTIFACTS_FILE, ERROR_FILE, EVENTS_FILE, METRICS_SUMMARY_FILE, RESULTS_FILE, RUN_DIR_ARTIFACTS,
    RUN_DIR_LOGS, RUN_MANIFEST_FILE,
};
use super::{RunId, RunStatus};

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
        metrics: read_json_or_default(&run.path.join(METRICS_SUMMARY_FILE), empty_object())?,
        results: read_json_or_default(&run.path.join(RESULTS_FILE), Value::Null)?,
        artifacts: read_json_lines(&run.path.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE))?,
        logs: read_json_lines(&run.path.join(RUN_DIR_LOGS).join(EVENTS_FILE))?,
        error: read_optional_text(&run.path.join(RUN_DIR_LOGS).join(ERROR_FILE))?,
        run,
    })
}

fn read_run_summaries(runs_dir: &Path) -> RlabResult<Vec<RunSummary>> {
    let mut runs = Vec::new();

    for entry in read_dir_entries(runs_dir)? {
        let entry = entry.map_err(|error| RlabError::io(runs_dir, error))?;
        let path = entry.path();

        if path.is_dir() {
            push_run_summary_if_valid(&mut runs, &path);
        }
    }

    Ok(runs)
}

fn push_run_summary_if_valid(runs: &mut Vec<RunSummary>, path: &Path) {
    if let Ok(run) = read_run(path) {
        runs.push(run_summary(run, path));
    }
}

fn read_dir_entries(path: &Path) -> RlabResult<fs::ReadDir> {
    fs::read_dir(path).map_err(|error| RlabError::io(path, error))
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
    path.join(RUN_MANIFEST_FILE)
}

fn read_run_file(path: &Path) -> RlabResult<RunDirectory> {
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    let run: RunDirectory = serde_json::from_str(&content).map_err(RlabError::serialization)?;

    run.validate_schema()?;

    Ok(run)
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

    let file = fs::File::open(path).map_err(|error| RlabError::io(path, error))?;
    let reader = BufReader::new(file);
    let mut values = Vec::new();

    for line in reader.lines() {
        let line = line.map_err(|error| RlabError::io(path, error))?;

        if line.trim().is_empty() {
            continue;
        }

        values.push(serde_json::from_str(&line).map_err(RlabError::serialization)?);
    }

    Ok(values)
}

fn read_optional_text(path: &Path) -> RlabResult<Option<String>> {
    if !path.exists() {
        return Ok(None);
    }

    fs::read_to_string(path)
        .map(Some)
        .map_err(|error| RlabError::io(path, error))
}

fn empty_object() -> Value {
    Value::Object(Default::default())
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

        let session = expect_ok(RunSession::create(
            &paths,
            "evaluation",
            "quick",
            vec!["rlab".to_string()],
            json!({}),
        ));

        let id = session.directory.id.as_str().to_string();

        expect_ok(session.append_metric(&crate::result::Metric {
            schema_version: 1,
            name: "score".to_string(),
            value: 0.75,
            unit: None,
            direction: None,
            timestamp: time::OffsetDateTime::now_utc(),
        }));

        expect_ok(session.complete(json!({"data": {"score": 0.75}})));

        let details = expect_ok(inspect_run(&paths, &id));

        assert_eq!(details.metrics["score"], 0.75);
        assert_eq!(details.results["data"]["score"], 0.75);
        assert_eq!(details.error, None);

        expect_ok(fs::remove_dir_all(root).map_err(|error| RlabError::Run {
            message: format!("failed to remove temporary run directory: {error}"),
        }));
    }

    fn temp_root(label: &str) -> PathBuf {
        let nonce = match SystemTime::now().duration_since(UNIX_EPOCH) {
            Ok(duration) => duration.as_nanos(),
            Err(error) => panic!("system clock is before UNIX_EPOCH: {error}"),
        };

        std::env::temp_dir().join(format!("rlab-{label}-{nonce}"))
    }

    fn expect_ok<T, E: std::fmt::Display>(result: Result<T, E>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }
}
