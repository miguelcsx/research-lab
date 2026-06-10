use serde::{Deserialize, Serialize};

use crate::jobs::JobRecord;
use crate::run::RunDirectory;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecRequest {
    pub schema_version: u32,
    pub name: String,
    pub command: Vec<String>,
    pub parser: Option<ExecParser>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecParser {
    pub module: String,
    pub function: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecRunSummary {
    pub schema_version: u32,
    pub run: RunDirectory,
    pub job: JobRecord,
}
