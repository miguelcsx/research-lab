use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, HostCommand, HostRequest,
    HostTarget, ProtocolVersion, RegistryKind, RlabResult, RunSession,
};

use crate::commands::run::{
    parse_params_public, parse_target, process_event_public, ParseTargetError, ParsedTarget,
};
use crate::host::process::run_python_host;
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct EvaluateCommand {
    pub suite: String,
    /// Target to evaluate. Accepts:
    ///   * a bare name (resolved as `model:<name>`),
    ///   * `<kind>:<name>` (e.g. `model:foo.bar`),
    ///   * `<kind>:<loader>:<path>` to load via a registered loader
    ///     (e.g. `model:hf:org/repo`).
    pub target: String,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param")]
    pub params: Vec<String>,
}

pub fn run(command: EvaluateCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let parsed = parse_target(&command.target, Some("model")).map_err(|error| match error {
        ParseTargetError::FilePath { value } => rlab_core::RlabError::Reference {
            message: format!(
                "'{value}' looks like a file path, but 'rlab evaluate' expects a registry target".
            ),
        },
        ParseTargetError::InvalidKind { value, reason } => rlab_core::RlabError::Reference {
            message: format!("invalid target kind in '{value}': {reason}"),
        },
        ParseTargetError::MissingName { value } => rlab_core::RlabError::Reference {
            message: format!("missing name in target '{value}' — expected <kind>:<name>"),
        },
    })?;
    let ParsedTarget { kind_str, name } = parsed;
    let mut params = parse_params_public(&command.params)?;
    if let serde_json::Value::Object(object) = &mut params {
        // Store the full `kind:ref` string so the runner can dispatch loader
        // refs (e.g. `model:hf:org/repo`) correctly. The target describes
        // the *thing being evaluated*, which is a different concept from
        // the run's `HostTarget.kind` (which is always `evaluation` here).
        // Even when the user passed a bare name on the CLI, we expand it
        // to `model:<name>` here so the runner has a single, consistent
        // dispatch format.
        object.insert(
            "target".to_string(),
            serde_json::Value::String(format!("{kind_str}:{name}")),
        );
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
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
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
        let metrics = rlab_core::run::inspect_run(&paths, run.id.as_str())?.metrics;
        if let Some(values) = metrics.as_object() {
            for (name, value) in values {
                print_line(&format!("  {name}: {value}"));
            }
        }
        print_line(&format!("inspect: rlab runs show {}", run.id.as_str()));
    }
    Ok(0)
}
