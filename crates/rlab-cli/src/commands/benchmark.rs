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
pub struct BenchmarkCommand {
    pub benchmark_name: String,
    /// Target to benchmark. Accepts a bare name (resolved as `model:<name>`),
    /// `<kind>:<name>` (e.g. `model:foo.bar`), or `<kind>:<loader>:<path>`
    /// (e.g. `model:hf:org/repo`).
    pub target: String,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param")]
    pub params: Vec<String>,
}

pub fn run(command: BenchmarkCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let parsed = parse_target(&command.target, Some("model")).map_err(|error| match error {
        ParseTargetError::FilePath { value } => rlab_core::RlabError::Reference {
            message: format!(
                "'{value}' looks like a file path, but 'rlab benchmark' expects a registry target.\n  \
                 Use the form: rlab benchmark <name> <kind>:<name>\n  \
                 Examples: rlab benchmark my.bench model:babylm.baseline.gpt2_strict_small\n           \
                           rlab benchmark my.bench model:hf:my-org/my-model\n  \
                 Run 'rlab discover' to list all registered targets."
            ),
        },
        ParseTargetError::InvalidKind { value, reason } => rlab_core::RlabError::Reference {
            message: format!("invalid target kind in '{value}': {reason}"),
        },
        ParseTargetError::MissingName { value } => rlab_core::RlabError::Reference {
            message: format!(
                "missing name in target '{value}' — expected <kind>:<name>, e.g. model:babylm.baseline.gpt2_strict_small"
            ),
        },
    })?;
    let ParsedTarget { kind_str, name } = parsed;
    let mut params = parse_params_public(&command.params)?;
    if let serde_json::Value::Object(object) = &mut params {
        // Always store the full `kind:ref` form so the runner has a single
        // dispatch format — even when the CLI accepted a bare name.
        object.insert(
            "target".to_string(),
            serde_json::Value::String(format!("{kind_str}:{name}")),
        );
    }
    let session = RunSession::create(
        &paths,
        RegistryKind::Benchmark.as_str(),
        &command.benchmark_name,
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
            kind: RegistryKind::Benchmark,
            name: command.benchmark_name.clone(),
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
            print_json("benchmark", run)?;
        } else {
            print_line(&format!("benchmark failed: {}", run.id.as_str()));
        }
        return Ok(1);
    }
    let result = match completed {
        Some(value) => value,
        None => serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}),
    };
    let run = session.complete(result)?;
    if json {
        print_json("benchmark", run)?;
    } else {
        print_line(&format!("completed benchmark run: {}", run.id.as_str()));
    }
    Ok(0)
}
