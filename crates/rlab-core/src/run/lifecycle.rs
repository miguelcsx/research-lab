
use std::fs;
use std::path::{Path, PathBuf};

const LOG_SCHEMA_VERSION: u32 = 1;
const ARTIFACT_SCHEMA_VERSION: u32 = 1;

use serde_json::{json, Value};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{append_line, ensure_dir, write_json_atomic, write_text_atomic, write_yaml_atomic, RunLock};
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
        ensure_dir(&path)?;
        for dir in [RUN_DIR_LOGS, RUN_DIR_ARTIFACTS, RUN_DIR_TABLES, RUN_DIR_FIGURES, RUN_DIR_RESULTS, RUN_DIR_EXTERNAL, RUN_DIR_REPRODUCIBILITY] {
            ensure_dir(&path.join(dir))?;
        }
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
        write_json_atomic(&path.join(RUN_MANIFEST_FILE), &directory)?;
        write_yaml_atomic(&path.join(RUN_MANIFEST_YAML_FILE), &directory)?;
        write_text_atomic(&path.join(STATUS_FILE), RunStatus::Created.as_str())?;
        write_json_atomic(&path.join(PARAMS_FILE), &directory.parameters)?;
        write_text_atomic(&path.join(NOTES_FILE), "")?;
        capture_reproducibility(paths, &directory)?;
        let mut session = Self { directory, lock };
        session.transition(RunStatus::Running)?;
        Ok(session)
    }

    pub fn append_metric(&self, metric: &Metric) -> RlabResult<()> {
        metric.validate()?;
        let line = serde_json::to_string(metric).map_err(RlabError::serialization)?;
        append_line(&self.directory.path.join(METRICS_FILE), &line)
    }

    pub fn append_log(&self, message: &str) -> RlabResult<()> {
        let event = json!({"schema_version": LOG_SCHEMA_VERSION, "message": message, "timestamp": OffsetDateTime::now_utc()});
        append_line(&self.directory.path.join(RUN_DIR_LOGS).join(EVENTS_FILE), &event.to_string())
    }

    pub fn append_note(&self, message: &str) -> RlabResult<()> {
        let event = json!({"schema_version": LOG_SCHEMA_VERSION, "text": message, "timestamp": OffsetDateTime::now_utc()});
        append_line(&self.directory.path.join(NOTES_FILE), &event.to_string())
    }

    pub fn save_artifact_reference(&self, artifact: &Value) -> RlabResult<()> {
        let staged = self.stage_artifact(artifact)?;
        append_line(&self.directory.path.join(RUN_DIR_ARTIFACTS).join(ARTIFACTS_FILE), &staged.to_string())
    }

    pub fn complete(mut self, result: Value) -> RlabResult<RunDirectory> {
        write_json_atomic(&self.directory.path.join(RESULTS_FILE), &result)?;
        self.write_metric_summary()?;
        self.transition(RunStatus::Completed)?;
        self.write_report()?;
        Ok(self.directory)
    }

    pub fn fail(mut self, message: &str) -> RlabResult<RunDirectory> {
        write_text_atomic(&self.directory.path.join(RUN_DIR_LOGS).join(ERROR_FILE), message)?;
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
                message: format!("invalid status transition: {} -> {}", self.directory.status.as_str(), next.as_str()),
            });
        }
        self.directory.status = next;
        self.directory.updated_at = OffsetDateTime::now_utc();
        write_json_atomic(&self.directory.path.join(RUN_MANIFEST_FILE), &self.directory)?;
        write_yaml_atomic(&self.directory.path.join(RUN_MANIFEST_YAML_FILE), &self.directory)?;
        write_text_atomic(&self.directory.path.join(STATUS_FILE), next.as_str())
    }

    fn stage_artifact(&self, artifact: &Value) -> RlabResult<Value> {
        let source_text = artifact.get("path").and_then(Value::as_str).ok_or_else(|| RlabError::Artifact {
            message: "artifact event is missing path".to_string(),
        })?;
        let source = PathBuf::from(source_text);
        if !source.is_file() {
            return Err(RlabError::Artifact { message: format!("artifact path is not a file: {}", source.display()) });
        }
        let name = artifact.get("name").and_then(Value::as_str).filter(|value| !value.trim().is_empty()).ok_or_else(|| RlabError::Artifact {
            message: "artifact event is missing name".to_string(),
        })?;
        let kind = match artifact.get("kind").and_then(Value::as_str) {
            Some(value) if !value.trim().is_empty() => value,
            _ => "file",
        };
        let file_name = safe_artifact_file_name(name, &source)?;
        let target_dir = self.directory.path.join(RUN_DIR_ARTIFACTS).join(kind);
        ensure_dir(&target_dir)?;
        let target = target_dir.join(file_name);
        fs::copy(&source, &target).map_err(|error| RlabError::io(&target, error))?;
        let mut staged = artifact.clone();
        if let Some(object) = staged.as_object_mut() {
            object.insert("staged_path".to_string(), Value::String(target.display().to_string()));
            object.insert("schema_version".to_string(), Value::Number(ARTIFACT_SCHEMA_VERSION.into()));
        }
        Ok(staged)
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
        write_text_atomic(&self.directory.path.join("report.md"), &report)
    }

    pub fn lock_path_exists(&self) -> bool {
        let _held = &self.lock;
        self.directory.path.join(RUN_LOCK_FILE).exists()
    }
}

fn safe_artifact_file_name(name: &str, source: &Path) -> RlabResult<String> {
    if name.contains(std::path::MAIN_SEPARATOR) || name.contains('/') || name.contains('\\') {
        return Err(RlabError::Artifact { message: format!("artifact name must not contain path separators: {name}") });
    }
    let extension = source.extension().and_then(|value| value.to_str());
    match extension {
        Some(ext) if !ext.trim().is_empty() => Ok(format!("{name}.{ext}")),
        _ => Ok(name.to_string()),
    }
}
