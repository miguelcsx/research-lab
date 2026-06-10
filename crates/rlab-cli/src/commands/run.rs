use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, HostCommand, HostEvent,
    HostRequest, HostTarget, ProtocolVersion, RegistryKind, RlabError, RlabResult, RunSession,
};

use crate::host::process::run_python_host;
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct RunCommand {
    pub target: String,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param")]
    pub params: Vec<String>,
}

pub fn run(command: RunCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let (kind, name) = parse_target(&command.target)?;
    let params = parse_params_public(&command.params)?;
    let session = RunSession::create(
        &paths,
        kind.as_str(),
        &name,
        std::env::args().collect(),
        params.clone(),
    )?;
    let request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: session.directory.id.as_str().to_string(),
        command: HostCommand::Execute,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: Some(HostTarget {
            kind,
            name: name.clone(),
        }),
        run_id: Some(session.directory.id.as_str().to_string()),
        params,
        seed: None,
        strict: command.strict || config.production.strict,
        environment: serde_json::json!({}),
    };
    let events = run_python_host(
        &config.python.executable,
        &config.python.runner_module,
        &request,
    )?;
    let mut completed = None;
    let mut failed = None;
    for event in &events {
        validate_event(event)?;
        process_event_public(&session, event, &mut completed, &mut failed)?;
    }
    if let Some(error) = failed {
        let run = session.fail(&error.to_string())?;
        if json {
            print_json("run", run)?;
        } else {
            print_line(&format!("run failed: {}", run.id.as_str()));
        }
        return Ok(1);
    }
    let result = match completed {
        Some(value) => value,
        None => serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}),
    };
    let run = session.complete(result)?;
    if json {
        print_json("run", run)?;
    } else {
        print_line(&format!("completed run: {}", run.id.as_str()));
    }
    Ok(0)
}

pub fn process_event_public(
    session: &RunSession,
    event: &HostEvent,
    completed: &mut Option<serde_json::Value>,
    failed: &mut Option<serde_json::Value>,
) -> RlabResult<()> {
    match event {
        HostEvent::Metric(value) => session.append_metric(&value.metric),
        HostEvent::Artifact(value) => session.save_artifact_reference(&value.artifact),
        HostEvent::Log(value) | HostEvent::Warning(value) => session.append_log(&value.message),
        HostEvent::Error(value) => session.append_log(&value.message),
        HostEvent::Completed { result, .. } => {
            *completed = Some(result.clone());
            Ok(())
        }
        HostEvent::Failed { error, .. } => {
            *failed = Some(error.clone());
            Ok(())
        }
        HostEvent::Batch { events, .. } => {
            for nested in events {
                process_event_public(session, nested, completed, failed)?;
            }
            Ok(())
        }
        HostEvent::RegistryRecord(_) => Ok(()),
    }
}

fn parse_target(value: &str) -> RlabResult<(RegistryKind, String)> {
    let mut parts = value.splitn(2, ':');
    let kind_str = match parts.next() {
        Some(text) if !text.trim().is_empty() => text,
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid target: {value}"),
            })
        }
    };
    let name = match parts.next() {
        Some(text) if !text.trim().is_empty() => text,
        _ => {
            return Err(RlabError::Reference {
                message: format!("target must be kind:name: {value}"),
            })
        }
    };
    Ok((RegistryKind::parse(kind_str)?, name.to_string()))
}

pub fn parse_params_public(params: &[String]) -> RlabResult<serde_json::Value> {
    let mut object = serde_json::Map::new();
    for param in params {
        let mut split = param.splitn(2, '=');
        let key = match split.next() {
            Some(text) if !text.trim().is_empty() => text,
            _ => {
                return Err(RlabError::Validation {
                    message: format!("invalid parameter: {param}"),
                })
            }
        };
        let raw_value = match split.next() {
            Some(text) => text,
            None => {
                return Err(RlabError::Validation {
                    message: format!("parameter must be key=value: {param}"),
                })
            }
        };
        object.insert(key.to_string(), parse_param_value(raw_value));
    }
    Ok(serde_json::Value::Object(object))
}

fn parse_param_value(value: &str) -> serde_json::Value {
    if value == "true" {
        return serde_json::Value::Bool(true);
    }
    if value == "false" {
        return serde_json::Value::Bool(false);
    }
    if let Ok(number) = value.parse::<i64>() {
        return serde_json::Value::Number(number.into());
    }
    if let Ok(number) = value.parse::<f64>() {
        if let Some(json_number) = serde_json::Number::from_f64(number) {
            return serde_json::Value::Number(json_number);
        }
    }
    serde_json::Value::String(value.to_string())
}
