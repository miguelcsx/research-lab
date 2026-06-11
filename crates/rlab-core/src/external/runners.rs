use std::path::PathBuf;
use std::process::{Command, Output};

use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

use super::{ExternalCommand, ExternalResult};

const SCHEMA_VERSION: u32 = 1;

const DOCKER_BINARY: &str = "docker";
const DOCKER_RUN_SUBCOMMAND: &str = "run";
const DOCKER_REMOVE_AFTER_EXIT_FLAG: &str = "--rm";
const DOCKER_VOLUME_FLAG: &str = "-v";
const DOCKER_WORKDIR_FLAG: &str = "-w";
const DOCKER_ENV_FLAG: &str = "-e";
const DOCKER_WORKSPACE: &str = "/workspace";

const DOCKER_IMAGE_ENV_KEY: &str = "RLAB_DOCKER_IMAGE";
const DEFAULT_DOCKER_IMAGE: &str = "python:3.11";

const EMPTY_ARGS_ERROR: &str = "external command args cannot be empty";

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExternalRunnerKind {
    Local,
    Subprocess,
    Docker,
}

pub fn run_external_command(
    command: &ExternalCommand,
    runner: ExternalRunnerKind,
) -> RlabResult<ExternalResult> {
    match runner {
        ExternalRunnerKind::Local | ExternalRunnerKind::Subprocess => run_process(command),
        ExternalRunnerKind::Docker => run_docker(command),
    }
}

fn run_process(command: &ExternalCommand) -> RlabResult<ExternalResult> {
    let invocation = CommandInvocation::from_external(command)?;
    let mut process = invocation.process_command();

    apply_process_context(command, &mut process);

    let output = process.output().map_err(|error| RlabError::Io {
        path: command_error_path(command),
        message: error.to_string(),
    })?;

    Ok(external_result(output))
}

fn apply_process_context(command: &ExternalCommand, process: &mut Command) {
    if let Some(cwd) = command.cwd.as_ref() {
        process.current_dir(cwd);
    }

    process.envs(command.env.iter());
}

fn run_docker(command: &ExternalCommand) -> RlabResult<ExternalResult> {
    let invocation = CommandInvocation::from_external(command)?;
    let output = docker_command(command, &invocation)
        .output()
        .map_err(|error| RlabError::Unsupported {
            feature: format!("docker external command failed to start: {error}"),
        })?;

    Ok(external_result(output))
}

struct CommandInvocation<'a> {
    program: &'a str,
    args: &'a [String],
}

impl<'a> CommandInvocation<'a> {
    fn from_external(command: &'a ExternalCommand) -> RlabResult<Self> {
        let program = first_arg(command)?;
        let args = remaining_args(command);

        Ok(Self { program, args })
    }

    fn process_command(&self) -> Command {
        let mut process = Command::new(self.program);
        process.args(self.args);
        process
    }
}

fn docker_command(command: &ExternalCommand, invocation: &CommandInvocation<'_>) -> Command {
    let mut docker = Command::new(DOCKER_BINARY);

    docker
        .arg(DOCKER_RUN_SUBCOMMAND)
        .arg(DOCKER_REMOVE_AFTER_EXIT_FLAG);

    apply_docker_workdir(command, &mut docker);
    apply_docker_environment(command, &mut docker);

    docker
        .arg(docker_image(command))
        .arg(invocation.program)
        .args(invocation.args);

    docker
}

fn apply_docker_workdir(command: &ExternalCommand, docker: &mut Command) {
    let Some(cwd) = command.cwd.as_ref() else {
        return;
    };

    docker
        .arg(DOCKER_VOLUME_FLAG)
        .arg(format!("{}:{DOCKER_WORKSPACE}", cwd.display()))
        .arg(DOCKER_WORKDIR_FLAG)
        .arg(DOCKER_WORKSPACE);
}

fn apply_docker_environment(command: &ExternalCommand, docker: &mut Command) {
    for (key, value) in &command.env {
        if key == DOCKER_IMAGE_ENV_KEY {
            continue;
        }

        docker.arg(DOCKER_ENV_FLAG).arg(format!("{key}={value}"));
    }
}

fn docker_image(command: &ExternalCommand) -> &str {
    match command.env.get(DOCKER_IMAGE_ENV_KEY) {
        Some(value) if !value.trim().is_empty() => value.as_str(),
        _ => DEFAULT_DOCKER_IMAGE,
    }
}

fn first_arg(command: &ExternalCommand) -> RlabResult<&str> {
    match command.args.first() {
        Some(value) if !value.trim().is_empty() => Ok(value),
        _ => Err(RlabError::Validation {
            message: EMPTY_ARGS_ERROR.to_owned(),
        }),
    }
}

fn remaining_args(command: &ExternalCommand) -> &[String] {
    match command.args.get(1..) {
        Some(args) => args,
        None => &[],
    }
}

fn command_error_path(command: &ExternalCommand) -> PathBuf {
    match command.cwd.as_ref() {
        Some(path) => path.to_path_buf(),
        None => std::env::temp_dir(),
    }
}

fn external_result(output: Output) -> ExternalResult {
    ExternalResult {
        schema_version: SCHEMA_VERSION,
        exit_code: output.status.code(),
        stdout: decode_output(output.stdout),
        stderr: decode_output(output.stderr),
    }
}

fn decode_output(bytes: Vec<u8>) -> String {
    String::from_utf8_lossy(&bytes).into_owned()
}
