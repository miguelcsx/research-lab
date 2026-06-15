use std::fs;
use std::io::{BufRead, BufReader};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use serde_json::{Map, Value};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::directory::RunDirectory;
use super::store::{
    ARTIFACTS_FILE, ERROR_FILE, EVENTS_FILE, METRICS_SUMMARY_FILE, PARAMS_FILE, RESULTS_FILE,
    RUN_DIR_ARTIFACTS, RUN_DIR_LOGS, RUN_MANIFEST_FILE,
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunRecord {
    pub run_id: String,
    pub path: PathBuf,
    pub manifest: Map<String, Value>,
    pub params: Map<String, Value>,
    pub metrics: Map<String, Value>,
}

pub fn query_run_records(
    root: &Path,
    target: Option<&str>,
    seed: Option<i64>,
) -> RlabResult<Vec<RunRecord>> {
    let mut records = all_run_records(root)?;
    records.retain(|record| {
        target
            .map(|pattern| wildcard_match(pattern, &target_name(record)))
            .unwrap_or(true)
            && seed_matches(record, seed)
    });
    Ok(records)
}

pub fn all_run_records(root: &Path) -> RlabResult<Vec<RunRecord>> {
    if !root.exists() {
        return Ok(Vec::new());
    }

    let mut records = Vec::new();
    for entry in read_dir_entries(root)? {
        let path = entry.map_err(|error| RlabError::io(root, error))?.path();
        if path.is_dir() && path.join(RUN_MANIFEST_FILE).is_file() {
            records.push(read_run_record(&path)?);
        }
    }
    records.sort_by(|left, right| left.run_id.cmp(&right.run_id));
    Ok(records)
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

fn read_run_record(path: &Path) -> RlabResult<RunRecord> {
    let manifest = read_json_object(&path.join(RUN_MANIFEST_FILE))?;
    let params = read_json_object_or_default(&path.join(PARAMS_FILE))?;
    let metrics = metrics_object(read_json_object_or_default(
        &path.join(METRICS_SUMMARY_FILE),
    )?);

    Ok(RunRecord {
        run_id: path
            .file_name()
            .map(|value| value.to_string_lossy().to_string())
            .unwrap_or_default(),
        path: path.to_path_buf(),
        manifest,
        params,
        metrics,
    })
}

fn read_json_object_or_default(path: &Path) -> RlabResult<Map<String, Value>> {
    if path.is_file() {
        read_json_object(path)
    } else {
        Ok(Map::new())
    }
}

fn read_json_object(path: &Path) -> RlabResult<Map<String, Value>> {
    match read_json_or_default(path, empty_object())? {
        Value::Object(value) => Ok(value),
        _ => Err(RlabError::serialization("expected JSON object")),
    }
}

fn metrics_object(raw: Map<String, Value>) -> Map<String, Value> {
    match raw.get("metrics") {
        Some(Value::Object(nested)) => numeric_metrics(nested),
        _ => numeric_metrics(&raw),
    }
}

fn numeric_metrics(raw: &Map<String, Value>) -> Map<String, Value> {
    raw.iter()
        .filter_map(|(name, value)| {
            value
                .as_f64()
                .map(|number| (name.clone(), Value::from(number)))
        })
        .collect()
}

fn target_name(record: &RunRecord) -> String {
    match record.manifest.get("target") {
        Some(Value::Object(target)) => format!(
            "{}:{}",
            target
                .get("kind")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            target
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or_default()
        ),
        Some(value) => value.as_str().unwrap_or_default().to_string(),
        None => format!(
            "{}:{}",
            record
                .manifest
                .get("operation")
                .and_then(Value::as_str)
                .unwrap_or_default(),
            record
                .manifest
                .get("name")
                .and_then(Value::as_str)
                .unwrap_or_default()
        ),
    }
}

fn seed_matches(record: &RunRecord, seed: Option<i64>) -> bool {
    seed.map(|expected| {
        record
            .manifest
            .get("seed")
            .or_else(|| record.params.get("seed"))
            .and_then(Value::as_i64)
            == Some(expected)
    })
    .unwrap_or(true)
}

fn wildcard_match(pattern: &str, value: &str) -> bool {
    let pattern = pattern.as_bytes();
    let value = value.as_bytes();
    let mut matched = vec![vec![false; value.len() + 1]; pattern.len() + 1];
    matched[0][0] = true;

    for row in 1..=pattern.len() {
        if pattern[row - 1] == b'*' {
            matched[row][0] = matched[row - 1][0];
        }
    }

    for row in 1..=pattern.len() {
        for col in 1..=value.len() {
            matched[row][col] = match pattern[row - 1] {
                b'*' => matched[row - 1][col] || matched[row][col - 1],
                b'?' => matched[row - 1][col - 1],
                byte => byte == value[col - 1] && matched[row - 1][col - 1],
            };
        }
    }

    matched[pattern.len()][value.len()]
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

    #[test]
    fn query_run_records_filters_target_and_seed() {
        let root = temp_root("query");
        let run = root.join("run-1");
        expect_ok(fs::create_dir_all(&run).map_err(|error| RlabError::io(&run, error)));
        expect_ok(
            fs::write(
                run.join(RUN_MANIFEST_FILE),
                r#"{"target":{"kind":"experiment","name":"demo"},"seed":7}"#,
            )
            .map_err(|error| RlabError::io(&run, error)),
        );
        expect_ok(
            fs::write(run.join(PARAMS_FILE), r#"{"model":"small"}"#)
                .map_err(|error| RlabError::io(&run, error)),
        );
        expect_ok(
            fs::write(
                run.join(METRICS_SUMMARY_FILE),
                r#"{"metrics":{"accuracy":0.75,"ok":true}}"#,
            )
            .map_err(|error| RlabError::io(&run, error)),
        );

        let records = expect_ok(query_run_records(&root, Some("experiment:*"), Some(7)));

        assert_eq!(records.len(), 1);
        assert_eq!(records[0].metrics["accuracy"], 0.75);
        assert!(records[0].metrics.get("ok").is_none());

        expect_ok(fs::remove_dir_all(root).map_err(|error| RlabError::Run {
            message: error.to_string(),
        }));
    }

    #[test]
    fn query_run_records_matches_current_run_manifest_shape() {
        let root = temp_root("query-current");
        let run = root.join("workflow_demo_20260101");
        expect_ok(fs::create_dir_all(&run).map_err(|error| RlabError::io(&run, error)));
        expect_ok(
            fs::write(
                run.join(RUN_MANIFEST_FILE),
                r#"{"operation":"workflow","name":"demo","parameters":{"seed":3}}"#,
            )
            .map_err(|error| RlabError::io(&run, error)),
        );
        expect_ok(
            fs::write(run.join(PARAMS_FILE), r#"{"seed":3}"#)
                .map_err(|error| RlabError::io(&run, error)),
        );

        let records = expect_ok(query_run_records(&root, Some("workflow:*"), Some(3)));

        assert_eq!(records.len(), 1);

        expect_ok(fs::remove_dir_all(root).map_err(|error| RlabError::Run {
            message: error.to_string(),
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
