use serde_json::json;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::jobs::start_job;
use crate::run::RunSession;

use super::request::{ExecRequest, ExecRunSummary};
const SCHEMA_VERSION: u32 = 1;

pub fn execute_tracked_command(paths: &ProjectPaths, request: ExecRequest) -> RlabResult<ExecRunSummary> {
    if request.schema_version != 1 {
        return Err(RlabError::Validation { message: format!("unsupported exec request schema version: {}", request.schema_version) });
    }
    if request.name.trim().is_empty() {
        return Err(RlabError::Validation { message: "exec run name cannot be empty".to_string() });
    }
    if request.command.is_empty() {
        return Err(RlabError::Validation { message: "exec command cannot be empty".to_string() });
    }
    let command_text = request.command.join(" ");
    let session = RunSession::create(paths, "exec", &request.name, vec!["rlab".to_string(), "exec".to_string(), command_text.clone()], json!({"command": command_text}))?;
    let job = start_job(paths, &command_text)?;
    let run = session.complete(json!({"schema_version":1,"job":job}))?;
    Ok(ExecRunSummary { schema_version: SCHEMA_VERSION, run, job })
}
