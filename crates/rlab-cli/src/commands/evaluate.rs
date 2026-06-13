use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, HostCommand, HostEvent,
    HostRequest, HostTarget, ProtocolVersion, RegistryKind, RlabError, RlabResult, RunDirectory,
    RunSession,
};
use serde_json::Value;

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

    let ParsedTarget { kind_str, name } = parse_evaluation_target(&command.target)?;
    let target_ref = format!("{kind_str}:{name}");
    let params = evaluation_params(&command.params, target_ref)?;

    let session = RunSession::create(
        &paths,
        RegistryKind::EVALUATION.as_str(),
        &command.suite,
        std::env::args().collect(),
        params.clone(),
    )?;

    let request = evaluation_request(
        &config,
        &paths,
        &session,
        &command.suite,
        params,
        command.strict,
    );

    let events = run_python_host(
        &config.python.executable,
        &config.python.runner_module,
        &request,
    )?;

    let outcome = process_events(&session, &events)?;

    match outcome {
        EvaluationOutcome::Failed(error) => {
            let run = session.fail(&error.to_string())?;
            report_failed_evaluation(&run, json)?;
            Ok(1)
        }
        EvaluationOutcome::Completed(result) => {
            let run = session.complete(result)?;
            report_completed_evaluation(&paths, &run, json)?;
            Ok(0)
        }
    }
}

enum EvaluationOutcome {
    Completed(Value),
    Failed(Value),
}

fn parse_evaluation_target(value: &str) -> RlabResult<ParsedTarget> {
    parse_target(value, Some("model")).map_err(evaluation_target_error)
}

fn evaluation_target_error(error: ParseTargetError) -> RlabError {
    match error {
        ParseTargetError::FilePath { value } => RlabError::Reference {
            message: format!(
                "'{value}' looks like a file path, but 'rlab evaluate' expects a registry target"
            ),
        },
        ParseTargetError::InvalidKind { value, reason } => RlabError::Reference {
            message: format!("invalid target kind in '{value}': {reason}"),
        },
        ParseTargetError::MissingName { value } => RlabError::Reference {
            message: format!("missing name in target '{value}' — expected <kind>:<name>"),
        },
    }
}

fn evaluation_params(params: &[String], target_ref: String) -> RlabResult<Value> {
    let mut params = parse_params_public(params)?;

    if let Value::Object(object) = &mut params {
        // Store the full `kind:ref` string so the runner can dispatch loader
        // refs (e.g. `model:hf:org/repo`) correctly. The target describes
        // the *thing being evaluated*, which is a different concept from
        // the run's `HostTarget.kind` (which is always `evaluation` here).
        // Even when the user passed a bare name on the CLI, we expand it
        // to `model:<name>` here so the runner has a single, consistent
        // dispatch format.
        object.insert("target".to_string(), Value::String(target_ref));
    }

    Ok(params)
}

fn evaluation_request(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    session: &RunSession,
    suite: &str,
    params: Value,
    strict: bool,
) -> HostRequest {
    let run_id = session.directory.id.as_str().to_string();

    HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: run_id.clone(),
        command: HostCommand::Execute,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: Some(HostTarget {
            kind: RegistryKind::EVALUATION,
            name: suite.to_string(),
        }),
        run_id: Some(run_id),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
        params,
        seed: None,
        strict: strict || config.production.strict,
        environment: empty_object(),
    }
}

fn process_events(session: &RunSession, events: &[HostEvent]) -> RlabResult<EvaluationOutcome> {
    let mut completed = None;
    let mut failed = None;

    for event in events {
        validate_event(event)?;
        process_event_public(session, event, &mut completed, &mut failed)?;
    }

    if let Some(error) = failed {
        return Ok(EvaluationOutcome::Failed(error));
    }

    let result = match completed {
        Some(value) => value,
        None => empty_result(),
    };

    Ok(EvaluationOutcome::Completed(result))
}

fn empty_object() -> Value {
    Value::Object(serde_json::Map::new())
}

fn empty_result() -> Value {
    serde_json::json!({
        "schema_version": SCHEMA_VERSION,
        "data": {}
    })
}

fn report_failed_evaluation(run: &RunDirectory, json: bool) -> RlabResult<()> {
    if json {
        print_json("evaluate", run)?;
    } else {
        print_line(&format!("evaluation failed: {}", run.id.as_str()));
    }

    Ok(())
}

fn report_completed_evaluation(
    paths: &ProjectPaths,
    run: &RunDirectory,
    json: bool,
) -> RlabResult<()> {
    if json {
        print_json("evaluate", run)?;
        return Ok(());
    }

    print_line(&format!("completed evaluation run: {}", run.id.as_str()));
    print_metrics(paths, run)?;
    print_line(&format!("inspect: rlab runs show {}", run.id.as_str()));

    Ok(())
}

fn print_metrics(paths: &ProjectPaths, run: &RunDirectory) -> RlabResult<()> {
    let metrics = rlab_core::run::inspect_run(paths, run.id.as_str())?.metrics;

    let Some(values) = metrics.as_object() else {
        return Ok(());
    };

    for (name, value) in values {
        print_line(&format!("  {name}: {value}"));
    }

    Ok(())
}
