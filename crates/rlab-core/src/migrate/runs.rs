use std::fs;
use std::path::Path;

use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::run::RunDirectory;

use super::plan::MigrationPlan;
use super::schema::CURRENT_SCHEMA_VERSION;

pub fn validate_run_manifest(run: &RunDirectory) -> RlabResult<()> {
    run.validate_schema()
}

pub fn scan_runs_for_migration(paths: &ProjectPaths, plan: &mut MigrationPlan) -> RlabResult<()> {
    if !paths.runs.exists() {
        return Ok(());
    }
    for entry in fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))? {
        let entry = entry.map_err(|error| RlabError::io(&paths.runs, error))?;
        let run_json = entry.path().join("run.json");
        if run_json.exists() {
            inspect_schema_file(&run_json, "run", plan)?;
        }
    }
    Ok(())
}

fn inspect_schema_file(path: &Path, kind: &str, plan: &mut MigrationPlan) -> RlabResult<()> {
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    let value: Value = serde_json::from_str(&content).map_err(RlabError::serialization)?;
    match value.get("schema_version").and_then(Value::as_u64) {
        Some(version) if version == u64::from(CURRENT_SCHEMA_VERSION) => Ok(()),
        Some(version) => {
            let version = u32::try_from(version).map_err(|_| RlabError::Validation {
                message: format!("schema_version is too large in {}", path.display()),
            })?;
            plan.push_upgrade(path.to_path_buf(), kind, version);
            Ok(())
        }
        None => {
            plan.push_missing_schema(path.to_path_buf(), kind);
            Ok(())
        }
    }
}
