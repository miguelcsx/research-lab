use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

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
