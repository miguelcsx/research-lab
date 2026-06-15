use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, load_effective_config, RegistryKind, RlabError, RlabResult, RunDirectory,
};
use serde_json::Value;

use crate::commands::run::{parse_params_public, parse_target, ParseTargetError, ParsedTarget};
use crate::host::execution::{self, ExecutionRequest};
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

    #[arg(long = "param", alias = "params")]
    pub params: Vec<String>,
}

pub fn run(command: EvaluateCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;

    let ParsedTarget { kind_str, name } = parse_evaluation_target(&command.target)?;
    let target_ref = format!("{kind_str}:{name}");
    let params = evaluation_params(&command.params, target_ref)?;

    let outcome = execution::execute_run(ExecutionRequest {
        config: &config,
        paths: &paths,
        operation: RegistryKind::EVALUATION.as_str(),
        name: &command.suite,
        target_kind: RegistryKind::EVALUATION,
        target_name: &command.suite,
        params,
        seed: None,
        strict: command.strict,
        default_result: empty_result(),
    })?;
    if outcome.failed {
        report_failed_evaluation(&outcome.run, json)?;
        Ok(1)
    } else {
        report_completed_evaluation(&paths, &outcome.run, json)?;
        Ok(0)
    }
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
