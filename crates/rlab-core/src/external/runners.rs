
use std::process::Command;

use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

use super::{ExternalCommand, ExternalResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExternalRunnerKind {
    Local,
    Subprocess,
    Docker,
}

pub fn run_external_command(command: &ExternalCommand, runner: ExternalRunnerKind) -> RlabResult<ExternalResult> {
    match runner {
        ExternalRunnerKind::Local | ExternalRunnerKind::Subprocess => run_process(command),
        ExternalRunnerKind::Docker => run_docker(command),
    }
}

fn run_process(command: &ExternalCommand) -> RlabResult<ExternalResult> {
    let program = first_arg(command)?;
    let mut process = Command::new(program);
    process.args(command.args.iter().skip(1));
    if let Some(cwd) = &command.cwd {
        process.current_dir(cwd);
    }
    process.envs(command.env.iter());
    let error_path = match &command.cwd { Some(path) => path.clone(), None => std::env::temp_dir() };
    let output = process.output().map_err(|error| RlabError::Io { path: error_path, message: error.to_string() })?;
    Ok(ExternalResult { schema_version: SCHEMA_VERSION, exit_code: output.status.code(), stdout: String::from_utf8_lossy(&output.stdout).to_string(), stderr: String::from_utf8_lossy(&output.stderr).to_string() })
}

fn run_docker(command: &ExternalCommand) -> RlabResult<ExternalResult> {
    let image = match command.env.get("RLAB_DOCKER_IMAGE") {
        Some(value) if !value.trim().is_empty() => value.as_str(),
        _ => "python:3.11",
    };
    let program = first_arg(command)?;
    let mut docker = Command::new("docker");
    docker.arg("run").arg("--rm");
    if let Some(cwd) = &command.cwd {
        docker.arg("-v").arg(format!("{}:/workspace", cwd.display()));
        docker.arg("-w").arg("/workspace");
    }
    for (key, value) in &command.env {
        if key != "RLAB_DOCKER_IMAGE" {
            docker.arg("-e").arg(format!("{key}={value}"));
        }
    }
    docker.arg(image).arg(program).args(command.args.iter().skip(1));
    let output = docker.output().map_err(|error| RlabError::Unsupported { feature: format!("docker external command failed to start: {error}") })?;
    Ok(ExternalResult { schema_version: SCHEMA_VERSION, exit_code: output.status.code(), stdout: String::from_utf8_lossy(&output.stdout).to_string(), stderr: String::from_utf8_lossy(&output.stderr).to_string() })
}

fn first_arg(command: &ExternalCommand) -> RlabResult<&str> {
    match command.args.first() {
        Some(value) if !value.trim().is_empty() => Ok(value),
        _ => Err(RlabError::Validation { message: "external command args cannot be empty".to_string() }),
    }
}
