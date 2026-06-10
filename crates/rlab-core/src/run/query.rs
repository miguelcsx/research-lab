use std::fs;
use std::path::Path;

use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::directory::RunDirectory;
use super::{RunId, RunStatus};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunSummary {
    pub id: String,
    pub operation: String,
    pub name: String,
    pub status: RunStatus,
    pub path: String,
}

pub fn list_runs(paths: &ProjectPaths) -> RlabResult<Vec<RunSummary>> {
    if !paths.runs.exists() {
        return Ok(Vec::new());
    }
    let mut runs = Vec::new();
    let entries = fs::read_dir(&paths.runs).map_err(|error| RlabError::io(&paths.runs, error))?;
    for entry in entries {
        let entry = entry.map_err(|error| RlabError::io(&paths.runs, error))?;
        let path = entry.path();
        if path.is_dir() {
            if let Ok(run) = read_run(&path) {
                runs.push(RunSummary {
                    id: run.id.as_str().to_string(),
                    operation: run.operation,
                    name: run.name,
                    status: run.status,
                    path: path.display().to_string(),
                });
            }
        }
    }
    runs.sort_by(|a, b| b.id.cmp(&a.id));
    Ok(runs)
}

pub fn show_run(paths: &ProjectPaths, id: &str) -> RlabResult<RunDirectory> {
    let run_id = RunId::parse(id.to_string())?;
    let path = paths.runs.join(run_id.as_str());
    read_run(&path)
}

fn read_run(path: &Path) -> RlabResult<RunDirectory> {
    let run_json = path.join("run.json");
    let content = fs::read_to_string(&run_json).map_err(|error| RlabError::io(&run_json, error))?;
    serde_json::from_str(&content).map_err(RlabError::serialization)
}
