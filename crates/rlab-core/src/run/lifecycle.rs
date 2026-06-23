use std::fs;
use std::path::{Path, PathBuf};

const LOG_SCHEMA_VERSION: u32 = 1;
const ARTIFACT_SCHEMA_VERSION: u32 = 1;
const ENV_PARENT_RUN_ID: &str = "RLAB_PARENT_RUN_ID";
const ENV_PARENT_TARGET: &str = "RLAB_PARENT_TARGET";

use serde_json::{Map, Value};
use time::OffsetDateTime;

use crate::artifact::{
    enforce_materialized_cap, prune_runs_keep_per_experiment, sweep_unreachable_objects,
    ArtifactStore, PromoteRequest,
};
use crate::config::{load_effective_config, ProjectPaths, StorageConfig};
use crate::error::{RlabError, RlabResult};
use crate::fs::{
    append_line, ensure_dir, write_json_atomic, write_text_atomic, write_yaml_atomic, RunLock,
};
use crate::reproducibility::capture_reproducibility;
use crate::result::Metric;

use super::storage::{apply_output_retention, relink_run_outputs, RUN_DIR_OUTPUTS};

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
    paths: ProjectPaths,
    storage: StorageConfig,
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
            parent_run_id: std::env::var(ENV_PARENT_RUN_ID).ok(),
            parent_target: std::env::var(ENV_PARENT_TARGET).ok(),
        };

        write_initial_run_files(&path, &directory)?;
        capture_reproducibility(paths, &directory)?;

        let storage = load_effective_config(Some(&paths.root), &[])
            .map(|config| config.storage)
            .unwrap_or_default();

        let mut session = Self {
            directory,
            paths: paths.clone(),
            storage,
            lock,
        };
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
        self.finalize_storage();

        Ok(self.directory)
    }

    /// Apply automatic storage management once a run has completed: prune
    /// resume-only checkpoint files (optimizer state) per the project's policy,
    /// refresh the affected content-addressed checkpoints, and reclaim the now
    /// orphaned objects. Best-effort: storage hygiene must never fail a run, so
    /// any error is recorded as a note and otherwise ignored.
    fn finalize_storage(&self) {
        if let Err(error) = self.run_finalize_storage() {
            let _ = self.append_note(&format!("storage finalize skipped: {error}"));
        }
    }

    fn run_finalize_storage(&self) -> RlabResult<()> {
        let outputs = self.directory.path.join(RUN_DIR_OUTPUTS);
        let report = apply_output_retention(&outputs, &self.storage.outputs, false)?;
        if !report.is_empty() {
            self.restage_changed_checkpoints(&report.changed)?;
            sweep_unreachable_objects(&self.paths, false)?;
        }
        // Collapse the run-directory checkpoint copies and the store into a single
        // physical copy (portable hard links), so identical checkpoints across runs
        // never cost twice.
        let _ = relink_run_outputs(&self.paths, &self.directory.path);
        // Cap the number of retained runs per experiment. Durable checkpoints are
        // safe in the CAS, so pruning old run directories only reclaims space.
        prune_runs_keep_per_experiment(
            &self.paths,
            self.storage.runs.keep_per_experiment,
            false,
        )?;
        // Keep the regenerable materialized cache bounded.
        enforce_materialized_cap(&self.paths, self.storage.materialized.max_gb, false)?;
        Ok(())
    }

    /// Re-ingest checkpoints whose files changed so their content-addressed trees,
    /// manifests, and the run's `artifacts.jsonl` no longer reference the removed
    /// optimizer-state blobs (which then become unreachable and are swept).
    fn restage_changed_checkpoints(&self, changed: &[PathBuf]) -> RlabResult<()> {
        restage_run_checkpoints(&self.paths, &self.artifacts_manifest_path(), changed)
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
        stage_artifact_into(&self.paths, artifact)
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

/// Ingest an artifact event into the content-addressed store (and promote it as a
/// semantic artifact when `artifact_kind` is set), returning the staged event with
/// `object_path`/`sha256`/`artifact_ref` filled in. Shared by live runs and the
/// retroactive `storage optimize` migration.
pub(crate) fn stage_artifact_into(paths: &ProjectPaths, artifact: &Value) -> RlabResult<Value> {
    let source = artifact_source(artifact)?;
    let name = artifact_name(artifact)?;
    let kind = artifact_kind(artifact);
    let store = ArtifactStore::new(paths);
    let stored = store.ingest_path(&source)?;
    let semantic = semantic_promote_request(artifact, &source)?;
    let manifest = match semantic {
        Some(request) => Some(store.promote(request)?),
        None => None,
    };
    let artifact_ref = manifest.as_ref().map(|value| {
        format!(
            "artifact:{}/{}@{}",
            value.reference.kind, value.reference.name, value.reference.version
        )
    });

    Ok(staged_artifact(
        artifact, name, kind, &source, &stored, artifact_ref,
    ))
}

/// Rewrite a run's `artifacts.jsonl` so the entries for `changed` checkpoint
/// directories are re-ingested (dropping references to removed optimizer-state
/// blobs). Used by both live completion and the retroactive migration.
pub(crate) fn restage_run_checkpoints(
    paths: &ProjectPaths,
    manifest_path: &Path,
    changed: &[PathBuf],
) -> RlabResult<()> {
    let Ok(content) = fs::read_to_string(manifest_path) else {
        return Ok(());
    };
    let mut lines = Vec::new();
    for line in content.lines() {
        if line.trim().is_empty() {
            continue;
        }
        let entry: Value = serde_json::from_str(line).map_err(RlabError::serialization)?;
        let is_changed = entry
            .get("path")
            .and_then(Value::as_str)
            .map(PathBuf::from)
            .is_some_and(|path| changed.contains(&path));
        if is_changed {
            lines.push(stage_artifact_into(paths, &entry)?.to_string());
        } else {
            lines.push(line.to_string());
        }
    }
    let mut body = lines.join("\n");
    body.push('\n');
    write_text_atomic(manifest_path, &body)
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
        message: format!(
            "artifact path is not a file or directory: {}",
            source.display()
        ),
    })
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

fn staged_artifact(
    artifact: &Value,
    name: &str,
    kind: &str,
    source: &Path,
    stored: &crate::artifact::StoredArtifact,
    artifact_ref: Option<String>,
) -> Value {
    let mut staged = artifact.clone();

    if let Some(object) = staged.as_object_mut() {
        object.insert(
            "schema_version".to_string(),
            Value::Number(ARTIFACT_SCHEMA_VERSION.into()),
        );
        object.insert("name".to_string(), Value::String(name.to_string()));
        object.insert("kind".to_string(), Value::String(kind.to_string()));
        object.insert(
            "path".to_string(),
            Value::String(source.display().to_string()),
        );
        object.insert("sha256".to_string(), Value::String(stored.sha256.clone()));
        object.insert(
            "storage_type".to_string(),
            Value::String(stored.storage_type.as_str().to_string()),
        );
        object.insert(
            "object_path".to_string(),
            Value::String(stored.object_path.display().to_string()),
        );
        object.insert(
            "size_bytes".to_string(),
            Value::Number(stored.size_bytes.into()),
        );
        if let Some(reference) = artifact_ref {
            object.insert("artifact_ref".to_string(), Value::String(reference));
        }
    }

    staged
}

fn semantic_promote_request(artifact: &Value, source: &Path) -> RlabResult<Option<PromoteRequest>> {
    let Some(artifact_kind) = optional_text(artifact, "artifact_kind") else {
        return Ok(None);
    };
    let artifact_name =
        optional_text(artifact, "artifact_name").ok_or_else(|| RlabError::Artifact {
            message: "artifact_name is required when artifact_kind is set".to_string(),
        })?;
    let version = optional_text(artifact, "artifact_version")
        .or_else(|| optional_text(artifact, "version"))
        .unwrap_or("")
        .to_string();
    Ok(Some(PromoteRequest {
        source: source.to_path_buf(),
        artifact_kind: artifact_kind.to_string(),
        name: artifact_name.to_string(),
        version,
        alias: optional_text(artifact, "alias").map(str::to_string),
    }))
}

fn optional_text<'a>(artifact: &'a Value, key: &str) -> Option<&'a str> {
    artifact
        .get(key)
        .and_then(Value::as_str)
        .filter(|value| !value.trim().is_empty())
}

#[cfg(test)]
mod tests {
    use serde_json::json;

    use crate::config::ProjectPaths;

    use super::*;

    #[test]
    fn stages_directory_artifacts() {
        let root = std::env::temp_dir().join(format!("rlab-dir-artifact-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let source = root.join("source");
        ensure_dir(&source).unwrap();
        std::fs::write(source.join("manifest.json"), "{}").unwrap();

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

        let manifest = session.artifact_dir().join("artifacts.jsonl");
        let content = std::fs::read_to_string(manifest).unwrap();
        assert!(content.contains("object_path"));
        assert!(content.contains("storage_type"));
        let _ = std::fs::remove_dir_all(root);
    }

    #[test]
    fn complete_prunes_optimizer_state_and_sweeps_orphans() {
        let root =
            std::env::temp_dir().join(format!("rlab-finalize-storage-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let paths = ProjectPaths {
            root: root.clone(),
            runs: root.join("runs"),
            artifacts: root.join("artifacts"),
            cache: root.join("cache"),
            registry_cache: root.join("registry"),
        };
        // The project opts into resume-only retention via its own lab.toml; rlab
        // applies nothing domain-specific by default.
        ensure_dir(&root).unwrap();
        std::fs::write(
            root.join("lab.toml"),
            "[storage.outputs]\nresume_only_globs = [\"runtime.pt\"]\nresume_pointer = \"checkpoint-latest.json\"\n",
        )
        .unwrap();
        let session =
            RunSession::create(&paths, "experiment", "demo", Vec::new(), json!({})).unwrap();
        let outputs = session.directory.path.join(RUN_DIR_OUTPUTS);

        // Two checkpoints: each with shared weights and unique optimizer state.
        for label in ["best", "final"] {
            let dir = outputs.join(format!("checkpoint-{label}"));
            ensure_dir(&dir).unwrap();
            std::fs::write(dir.join("model.safetensors"), b"shared-weights").unwrap();
            std::fs::write(dir.join("runtime.pt"), format!("optimizer-{label}")).unwrap();
            session
                .save_artifact_reference(&json!({
                    "path": dir,
                    "name": format!("checkpoint.{label}"),
                    "kind": "directory",
                    "artifact_kind": "checkpoint",
                    "artifact_name": "demo",
                    "artifact_version": label,
                    "alias": label,
                }))
                .unwrap();
        }
        std::fs::write(
            outputs.join("checkpoint-latest.json"),
            json!({"checkpoint_path": outputs.join("checkpoint-final"), "label": "final"})
                .to_string(),
        )
        .unwrap();

        session.complete(json!({"schema_version": 1})).unwrap();

        // Resume checkpoint keeps optimizer state; the other has it stripped.
        assert!(outputs.join("checkpoint-final/runtime.pt").exists());
        assert!(!outputs.join("checkpoint-best/runtime.pt").exists());
        assert!(outputs.join("checkpoint-best/model.safetensors").exists());

        // The orphaned optimizer blob ("optimizer-best") must be swept from the CAS,
        // while the resume one ("optimizer-final") and the shared weights remain.
        let blobs = paths.artifacts.join("objects").join("blobs");
        let mut contents = Vec::new();
        for entry in walkdir::WalkDir::new(&blobs).into_iter().flatten() {
            if entry.file_type().is_file() {
                contents.push(std::fs::read_to_string(entry.path()).unwrap_or_default());
            }
        }
        assert!(contents.iter().any(|body| body == "shared-weights"));
        assert!(contents.iter().any(|body| body == "optimizer-final"));
        assert!(
            !contents.iter().any(|body| body == "optimizer-best"),
            "orphaned optimizer blob should have been swept"
        );

        // The surviving weights are a single physical copy: the run-directory file
        // is hard-linked to the store blob (same inode, link count >= 2).
        #[cfg(unix)]
        {
            use std::os::unix::fs::MetadataExt;
            let weights = outputs.join("checkpoint-final/model.safetensors");
            let meta = std::fs::metadata(&weights).unwrap();
            assert!(
                meta.nlink() >= 2,
                "checkpoint weights should be hard-linked to the store"
            );
        }
        let _ = std::fs::remove_dir_all(root);
    }
}
