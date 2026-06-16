use std::fs;
use std::path::{Path, PathBuf};

const LOG_SCHEMA_VERSION: u32 = 1;
const ARTIFACT_SCHEMA_VERSION: u32 = 1;

use serde_json::{Map, Value};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{
    append_line, ensure_dir, write_json_atomic, write_text_atomic, write_yaml_atomic, RunLock,
};
use crate::reproducibility::capture_reproducibility;
use crate::result::Metric;

use super::directory::{RunDirectory, RUN_SCHEMA_VERSION};
use super::lock::RUN_LOCK_FILE;
use super::store::{
    write_metric_summary, ARTIFACTS_FILE, ERROR_FILE, EVENTS_FILE, METRICS_FILE, NOTES_FILE,
    PARAMS_FILE, RESULTS_FILE, RUN_DIR_ARTIFACTS, RUN_DIR_EXTERNAL, RUN_DIR_FIGURES, RUN_DIR_LOGS,
    RUN_DIR_REPRODUCIBILITY, RUN_DIR_RESULTS, RUN_DIR_TABLES, RUN_MANIFEST_FILE,
    RUN_MANIFEST_YAML_FILE, STATUS_FILE,
};
use super::{RunId, RunStatus};

#[derive(Debug)]
pub struct RunSession {
    pub directory: RunDirectory,
    lock: RunLock,
}

impl RunSession {
    pub fn create(
        paths: &ProjectPaths,
        operation: &str,
        name: &str,
        command: Vec<String>,
        parameters: Value,
    ) -> RlabResult<Self> {
        paths.ensure_base_dirs()?;

        let id = RunId::new(operation, name)?;
        let path = paths.runs.join(id.as_str());

        create_run_dirs(&path)?;

        let lock = RunLock::acquire(&path)?;
        let now = OffsetDateTime::now_utc();

        let directory = RunDirectory {
            schema_version: RUN_SCHEMA_VERSION,
            id,
            operation: operation.to_string(),
            name: name.to_string(),
            status: RunStatus::Created,
            path: path.clone(),
            created_at: now,
            updated_at: now,
            command,
            parameters,
            notes: None,
        };

        write_initial_run_files(&path, &directory)?;
        capture_reproducibility(paths, &directory)?;

        let mut session = Self { directory, lock };
        session.transition(RunStatus::Running)?;

        Ok(session)
    }

    pub fn append_metric(&self, metric: &Metric) -> RlabResult<()> {
        metric.validate()?;

        let line = serde_json::to_string(metric).map_err(RlabError::serialization)?;
        append_line(&self.metric_path(), &line)
    }

    pub fn append_log(&self, message: &str) -> RlabResult<()> {
        append_line(&self.log_events_path(), &event_line("message", message))
    }

    pub fn append_note(&self, message: &str) -> RlabResult<()> {
        append_line(&self.notes_path(), &event_line("text", message))
    }

    pub fn save_artifact_reference(&self, artifact: &Value) -> RlabResult<()> {
        let staged = self.stage_artifact(artifact)?;

        append_line(&self.artifacts_manifest_path(), &staged.to_string())
    }

    pub fn complete(mut self, result: Value) -> RlabResult<RunDirectory> {
        write_json_atomic(&self.results_path(), &result)?;
        self.write_metric_summary()?;
        self.transition(RunStatus::Completed)?;
        self.write_report()?;

        Ok(self.directory)
    }

    pub fn fail(mut self, message: &str) -> RlabResult<RunDirectory> {
        write_text_atomic(&self.error_path(), message)?;
        self.write_metric_summary()?;
        self.transition(RunStatus::Failed)?;
        self.write_report()?;

        Ok(self.directory)
    }

    pub fn fail_with_result(mut self, message: &str, result: Value) -> RlabResult<RunDirectory> {
        write_json_atomic(&self.results_path(), &result)?;
        write_text_atomic(&self.error_path(), message)?;
        self.write_metric_summary()?;
        self.transition(RunStatus::Failed)?;
        self.write_report()?;

        Ok(self.directory)
    }

    pub fn artifact_dir(&self) -> PathBuf {
        self.directory.path.join(RUN_DIR_ARTIFACTS)
    }

    fn transition(&mut self, next: RunStatus) -> RlabResult<()> {
        if !self.directory.status.can_transition_to(next) {
            return Err(RlabError::Run {
                message: format!(
                    "invalid status transition: {} -> {}",
                    self.directory.status.as_str(),
                    next.as_str()
                ),
            });
        }

        self.directory.status = next;
        self.directory.updated_at = OffsetDateTime::now_utc();

        self.write_manifest()?;
        write_text_atomic(&self.status_path(), next.as_str())
    }

    fn stage_artifact(&self, artifact: &Value) -> RlabResult<Value> {
        let source = artifact_source(artifact)?;
        let name = artifact_name(artifact)?;
        let kind = artifact_kind(artifact);
        let file_name = safe_artifact_file_name(name, &source)?;
        let target_dir = self.artifact_dir().join(kind);

        ensure_dir(&target_dir)?;

        let target = target_dir.join(file_name);

        copy_artifact(&source, &target)?;

        Ok(staged_artifact(artifact, &target))
    }

    fn write_metric_summary(&self) -> RlabResult<()> {
        write_metric_summary(&self.directory.path).map(|_| ())
    }

    fn write_report(&self) -> RlabResult<()> {
        let report = format!(
            "# rlab run {id}\n\n- operation: `{operation}`\n- name: `{name}`\n- status: `{status}`\n",
            id = self.directory.id.as_str(),
            operation = self.directory.operation,
            name = self.directory.name,
            status = self.directory.status.as_str(),
        );

        write_text_atomic(&self.report_path(), &report)
    }

    fn write_manifest(&self) -> RlabResult<()> {
        write_json_atomic(&self.manifest_path(), &self.directory)?;
        write_yaml_atomic(&self.manifest_yaml_path(), &self.directory)
    }

    pub fn lock_path_exists(&self) -> bool {
        let _held = &self.lock;

        self.directory.path.join(RUN_LOCK_FILE).exists()
    }

    fn manifest_path(&self) -> PathBuf {
        self.directory.path.join(RUN_MANIFEST_FILE)
    }

    fn manifest_yaml_path(&self) -> PathBuf {
        self.directory.path.join(RUN_MANIFEST_YAML_FILE)
    }

    fn status_path(&self) -> PathBuf {
        self.directory.path.join(STATUS_FILE)
    }

    fn metric_path(&self) -> PathBuf {
        self.directory.path.join(METRICS_FILE)
    }

    fn notes_path(&self) -> PathBuf {
        self.directory.path.join(NOTES_FILE)
    }

    fn results_path(&self) -> PathBuf {
        self.directory.path.join(RESULTS_FILE)
    }

    fn report_path(&self) -> PathBuf {
        self.directory.path.join("report.md")
    }

    fn log_events_path(&self) -> PathBuf {
        self.directory.path.join(RUN_DIR_LOGS).join(EVENTS_FILE)
    }

    fn error_path(&self) -> PathBuf {
        self.directory.path.join(RUN_DIR_LOGS).join(ERROR_FILE)
    }

    fn artifacts_manifest_path(&self) -> PathBuf {
        self.artifact_dir().join(ARTIFACTS_FILE)
    }
}

fn create_run_dirs(path: &Path) -> RlabResult<()> {
    ensure_dir(path)?;

    for dir in [
        RUN_DIR_LOGS,
        RUN_DIR_ARTIFACTS,
        RUN_DIR_TABLES,
        RUN_DIR_FIGURES,
        RUN_DIR_RESULTS,
        RUN_DIR_EXTERNAL,
        RUN_DIR_REPRODUCIBILITY,
    ] {
        ensure_dir(&path.join(dir))?;
    }

    Ok(())
}

fn write_initial_run_files(path: &Path, directory: &RunDirectory) -> RlabResult<()> {
    write_json_atomic(&path.join(RUN_MANIFEST_FILE), directory)?;
    write_yaml_atomic(&path.join(RUN_MANIFEST_YAML_FILE), directory)?;
    write_text_atomic(&path.join(STATUS_FILE), RunStatus::Created.as_str())?;
    write_json_atomic(&path.join(PARAMS_FILE), &directory.parameters)?;
    write_text_atomic(&path.join(NOTES_FILE), "")
}

fn event_line(field: &str, message: &str) -> String {
    let mut event = Map::with_capacity(3);

    event.insert(
        "schema_version".to_string(),
        Value::Number(LOG_SCHEMA_VERSION.into()),
    );
    event.insert(field.to_string(), Value::String(message.to_string()));
    event.insert(
        "timestamp".to_string(),
        Value::String(OffsetDateTime::now_utc().to_string()),
    );

    Value::Object(event).to_string()
}

fn artifact_source(artifact: &Value) -> RlabResult<PathBuf> {
    let source_text = artifact
        .get("path")
        .and_then(Value::as_str)
        .ok_or_else(|| RlabError::Artifact {
            message: "artifact event is missing path".to_string(),
        })?;

    let source = PathBuf::from(source_text);

    if source.is_file() || source.is_dir() {
        return Ok(source);
    }

    Err(RlabError::Artifact {
        message: format!("artifact path does not exist: {}", source.display()),
    })
}

fn copy_artifact(source: &Path, target: &Path) -> RlabResult<()> {
    if source.is_dir() {
        copy_dir(source, target)
    } else {
        fs::copy(source, target)
            .map(|_| ())
            .map_err(|error| RlabError::io(target, error))
    }
}

fn copy_dir(source: &Path, target: &Path) -> RlabResult<()> {
    ensure_dir(target)?;
    for entry in fs::read_dir(source).map_err(|error| RlabError::io(source, error))? {
        let entry = entry.map_err(|error| RlabError::io(source, error))?;
        let path = entry.path();
        let destination = target.join(entry.file_name());
        if path.is_dir() {
            copy_dir(&path, &destination)?;
        } else {
            fs::copy(&path, &destination).map_err(|error| RlabError::io(&destination, error))?;
        }
    }
    Ok(())
}

fn artifact_name(artifact: &Value) -> RlabResult<&str> {
    artifact
        .get("name")
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .ok_or_else(|| RlabError::Artifact {
            message: "artifact event is missing name".to_string(),
        })
}

fn artifact_kind(artifact: &Value) -> &str {
    match artifact.get("kind").and_then(Value::as_str) {
        Some(value) if !value.trim().is_empty() => value,
        _ => "file",
    }
}

fn staged_artifact(artifact: &Value, target: &Path) -> Value {
    let mut staged = artifact.clone();

    if let Some(object) = staged.as_object_mut() {
        object.insert(
            "staged_path".to_string(),
            Value::String(target.display().to_string()),
        );
        object.insert(
            "schema_version".to_string(),
            Value::Number(ARTIFACT_SCHEMA_VERSION.into()),
        );
    }

    staged
}

fn safe_artifact_file_name(name: &str, source: &Path) -> RlabResult<String> {
    if contains_path_separator(name) {
        return Err(RlabError::Artifact {
            message: format!("artifact name must not contain path separators: {name}"),
        });
    }

    match source.extension().and_then(|value| value.to_str()) {
        Some(extension) if !extension.trim().is_empty() => Ok(format!("{name}.{extension}")),
        _ => Ok(name.to_string()),
    }
}

fn contains_path_separator(value: &str) -> bool {
    value.contains(std::path::MAIN_SEPARATOR) || value.contains('/') || value.contains('\\')
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use crate::config::ProjectPaths;

    use super::*;

    #[test]
    fn stages_directory_artifacts() {
        let root = std::env::temp_dir().join(format!("rlab-dir-artifact-{}", std::process::id()));
        let _ = fs::remove_dir_all(&root);
        let source = root.join("source");
        ensure_dir(&source).unwrap();
        fs::write(source.join("manifest.json"), "{}").unwrap();

        let paths = ProjectPaths {
            root: root.clone(),
            runs: root.join("runs"),
            artifacts: root.join("artifacts"),
            cache: root.join("cache"),
            registry_cache: root.join("registry"),
        };
        let session =
            RunSession::create(&paths, "workflow", "tokenizer", Vec::new(), json!({})).unwrap();

        session
            .save_artifact_reference(&json!({
                "path": source,
                "name": "tokenizer",
                "kind": "directory",
            }))
            .unwrap();

        assert!(session
            .artifact_dir()
            .join("directory")
            .join("tokenizer")
            .join("manifest.json")
            .exists());
        let _ = fs::remove_dir_all(root);
    }
}
