use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, HostCommand, HostRequest,
    HostTarget, ProtocolVersion, RegistryKind, RlabResult, RunSession,
};

use crate::commands::run::{parse_params_public, process_event_public};
use crate::host::process::run_python_host;
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct EvaluateCommand {
    pub suite: String,
    #[arg(long)]
    pub model: String,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param")]
    pub params: Vec<String>,
}

pub fn run(command: EvaluateCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let mut params = parse_params_public(&command.params)?;
    // Accept bare component names (`--model my.model`) by prepending the
    // `model:` kind prefix that `_resolve_component` expects. Users that
    // want a different kind (e.g. `hf:org/repo`) can still pass the full
    // `kind:name` form and it will be left untouched.
    let model_ref = if command.model.contains(':') {
        command.model.clone()
    } else {
        format!("model:{}", command.model)
    };
    if let serde_json::Value::Object(object) = &mut params {
        object.insert("model".to_string(), serde_json::Value::String(model_ref));
    }
    let session = RunSession::create(
        &paths,
        RegistryKind::Evaluation.as_str(),
        &command.suite,
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
            kind: RegistryKind::Evaluation,
            name: command.suite.clone(),
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
            print_json("evaluate", run)?;
        } else {
            print_line(&format!("evaluation failed: {}", run.id.as_str()));
        }
        return Ok(1);
    }
    let result = match completed {
        Some(value) => value,
        None => serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}),
    };
    let run = session.complete(result)?;
    if json {
        print_json("evaluate", run)?;
    } else {
        print_line(&format!("completed evaluation run: {}", run.id.as_str()));
    }
    Ok(0)
}
