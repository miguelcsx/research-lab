use std::fs;

use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunErrorReport {
    pub schema_version: u32,
    pub run_id: String,
    pub error: String,
}

pub fn render_run_error(paths: &ProjectPaths, run_id: &str) -> RlabResult<RunErrorReport> {
    let path = paths.runs.join(run_id).join("logs/error.txt");
    if !path.exists() {
        return Err(RlabError::NotFound { subject: format!("error log for run {run_id}") });
    }
    let error = fs::read_to_string(&path).map_err(|source| RlabError::io(&path, source))?;
    Ok(RunErrorReport { schema_version: SCHEMA_VERSION, run_id: run_id.to_string(), error })
}
