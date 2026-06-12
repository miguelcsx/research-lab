use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config,
    registry::load_registry_cache, run::list_runs, EffectiveConfig, Grid, HostCommand, HostEvent,
    HostRequest, HostTarget, ProtocolVersion, RegistryKind, RlabError, RlabResult, RunDirectory,
    RunSession, RunStatus,
};
use serde_json::Value;

use crate::commands::discover::cache_key_for;
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

struct RunOutcome {
    run: RunDirectory,
    failed: bool,
}

pub fn run(command: RunCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let (kind, name) = parse_target_kind(&command.target)?;
    let params = resolve_param_refs(&paths, parse_params_public(&command.params)?)?;
    let strict = command.strict || config.production.strict;

    // A target that declares a `matrix` (e.g. an experiment) is run once per
    // grid cell as its own tracked run — comparable via `rlab compare`.
    let cells = matrix_cells(&config, &paths, strict, &kind, &name)?;
    if cells.is_empty() {
        let outcome = execute_run(&config, &paths, &kind, &name, params, strict)?;
        return report_run(&outcome, json);
    }

    if !json {
        print_line(&format!("sweep: {} configs", cells.len()));
    }
    let mut outcomes = Vec::with_capacity(cells.len());
    for cell in &cells {
        let merged = merge_params(&params, cell);
        let outcome = execute_run(&config, &paths, &kind, &name, merged, strict)?;
        if !json {
            let status = if outcome.failed {
                "failed"
            } else {
                "completed"
            };
            print_line(&format!(
                "  {status} {} -> {}",
                format_cell(cell),
                outcome.run.id.as_str()
            ));
        }
        outcomes.push(outcome);
    }
    report_sweep(&outcomes, json)
}

/// Run a single target invocation and finalize its session.
fn execute_run(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    kind: &RegistryKind,
    name: &str,
    params: Value,
    strict: bool,
) -> RlabResult<RunOutcome> {
    let session = RunSession::create(
        paths,
        kind.as_str(),
        name,
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
            kind: kind.clone(),
            name: name.to_string(),
        }),
        run_id: Some(session.directory.id.as_str().to_string()),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
        params,
        seed: None,
        strict,
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
        return Ok(RunOutcome { run, failed: true });
    }
    let result = completed
        .unwrap_or_else(|| serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}));
    let run = session.complete(result)?;
    Ok(RunOutcome { run, failed: false })
}

/// Expand the target's declared `matrix` metadata into grid cells.
///
/// Read from the cached registry only (no Python round-trip), so ordinary runs
/// pay no overhead. If the registry has not been discovered yet, or the target
/// declares no matrix, this returns no cells and the target runs once.
fn matrix_cells(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    strict: bool,
    kind: &RegistryKind,
    name: &str,
) -> RlabResult<Vec<BTreeMap<String, Value>>> {
    let cache_key = cache_key_for(config, strict)?;
    let Some(registry) = load_registry_cache(&paths.registry_cache, &cache_key)? else {
        return Ok(Vec::new());
    };
    let Some(record) = registry.find(kind.clone(), name) else {
        return Ok(Vec::new());
    };
    let Some(matrix) = record.metadata.get("matrix") else {
        return Ok(Vec::new());
    };
    let axes: BTreeMap<String, Vec<Value>> = match serde_json::from_value(matrix.clone()) {
        Ok(axes) => axes,
        Err(_) => return Ok(Vec::new()),
    };
    if axes.is_empty() {
        return Ok(Vec::new());
    }
    Grid::new(axes)?.expand()
}

fn merge_params(base: &Value, cell: &BTreeMap<String, Value>) -> Value {
    let mut object = base.as_object().cloned().unwrap_or_default();
    for (key, value) in cell {
        object.insert(key.clone(), value.clone());
    }
    Value::Object(object)
}

/// Resolve `@<kind>:<name>[/suffix]` param values to the latest completed run's
/// output path, so pipeline stages reference each other without pasting run ids.
fn resolve_param_refs(paths: &ProjectPaths, params: Value) -> RlabResult<Value> {
    let Value::Object(map) = params else {
        return Ok(params);
    };
    let mut resolved = serde_json::Map::with_capacity(map.len());
    for (key, value) in map {
        let value = match &value {
            Value::String(text) if text.starts_with('@') => {
                Value::String(resolve_run_reference(paths, text)?)
            }
            _ => value,
        };
        resolved.insert(key, value);
    }
    Ok(Value::Object(resolved))
}

fn resolve_run_reference(paths: &ProjectPaths, reference: &str) -> RlabResult<String> {
    let (target, suffix) = match reference[1..].split_once('/') {
        Some((target, suffix)) => (target, Some(suffix)),
        None => (&reference[1..], None),
    };
    let (kind, name) = target
        .split_once(':')
        .ok_or_else(|| RlabError::Validation {
            message: format!(
                "invalid run reference '{reference}': expected @<kind>:<name>[/suffix]"
            ),
        })?;
    let latest = list_runs(paths)?
        .into_iter()
        .filter(|run| {
            run.operation == kind && run.name == name && run.status == RunStatus::Completed
        })
        .max_by(|left, right| left.id.cmp(&right.id))
        .ok_or_else(|| RlabError::Validation {
            message: format!("no completed run for '{kind}:{name}' referenced by '{reference}'"),
        })?;
    let mut path = PathBuf::from(latest.path);
    if let Some(suffix) = suffix {
        path.push(suffix);
    }
    Ok(path.to_string_lossy().into_owned())
}

fn format_cell(cell: &BTreeMap<String, Value>) -> String {
    cell.iter()
        .map(|(key, value)| format!("{key}={value}"))
        .collect::<Vec<_>>()
        .join(", ")
}

fn report_run(outcome: &RunOutcome, json: bool) -> RlabResult<u8> {
    if json {
        print_json("run", &outcome.run)?;
    } else if outcome.failed {
        print_line(&format!("run failed: {}", outcome.run.id.as_str()));
    } else {
        print_line(&format!("completed run: {}", outcome.run.id.as_str()));
    }
    Ok(u8::from(outcome.failed))
}

fn report_sweep(outcomes: &[RunOutcome], json: bool) -> RlabResult<u8> {
    let failures = outcomes.iter().filter(|outcome| outcome.failed).count();
    if json {
        let ids: Vec<&str> = outcomes
            .iter()
            .map(|outcome| outcome.run.id.as_str())
            .collect();
        print_json(
            "sweep",
            serde_json::json!({"runs": ids, "failures": failures}),
        )?;
    } else {
        print_line(&format!(
            "sweep complete: {} runs, {} failed",
            outcomes.len(),
            failures
        ));
    }
    Ok(u8::from(failures > 0))
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

pub struct ParsedTarget {
    pub kind_str: String,
    pub name: String,
}

#[derive(Debug)]
pub enum ParseTargetError {
    FilePath { value: String },
    InvalidKind { value: String, reason: String },
    MissingName { value: String },
}

/// Parse a `<kind>:<name>` reference. Used by `rlab run` and `rlab evaluate`.
///
/// If `default_kind` is provided and the value contains no `:`, the parsed
/// kind is set to `default_kind` and the entire value is used as the name.
/// This lets subcommands whose target always has the same kind (e.g. `rlab
/// evaluate <suite> <model-name>`) accept a bare name.
pub fn parse_target(
    value: &str,
    default_kind: Option<&str>,
) -> Result<ParsedTarget, ParseTargetError> {
    // Detect file paths early and give an actionable error. We only flag
    // values that *look* like paths (start with `/`, `./`, `../`, or `\`,
    // or end in `.py`/`.toml`) so that 3-segment refs like
    // `model:hf:org/repo` (which contain `/` in the path portion) are
    // still accepted.
    if value.ends_with(".py")
        || value.ends_with(".toml")
        || value.starts_with('/')
        || value.starts_with("./")
        || value.starts_with("../")
        || value.starts_with('\\')
    {
        return Err(ParseTargetError::FilePath {
            value: value.to_string(),
        });
    }
    if !value.contains(':') {
        if let Some(kind) = default_kind {
            return Ok(ParsedTarget {
                kind_str: kind.to_string(),
                name: value.to_string(),
            });
        }
        return Err(ParseTargetError::InvalidKind {
            value: value.to_string(),
            reason: "expected <kind>:<name>".to_string(),
        });
    }
    let mut parts = value.splitn(2, ':');
    let kind_str = match parts.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(ParseTargetError::InvalidKind {
                value: value.to_string(),
                reason: "expected <kind>:<name>".to_string(),
            });
        }
    };
    let name = match parts.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(ParseTargetError::MissingName {
                value: value.to_string(),
            });
        }
    };
    Ok(ParsedTarget { kind_str, name })
}

fn parse_target_kind(value: &str) -> RlabResult<(RegistryKind, String)> {
    let parsed = parse_target(value, None).map_err(|error| match error {
        ParseTargetError::FilePath { value } => RlabError::Reference {
            message: format!(
                "'{value}' looks like a file path, but 'rlab run' expects a registry target.\n  \
                 Use the form: rlab run <kind>:<name>\n  \
                 Examples: rlab run dataset:babylm.curation.smoke\n           rlab run experiment:my.experiment\n  \
                 Run 'rlab discover' to list all registered targets."
            ),
        },
        ParseTargetError::InvalidKind { value, reason } => RlabError::Reference {
            message: format!("invalid target: '{value}' — {reason}"),
        },
        ParseTargetError::MissingName { value } => RlabError::Reference {
            message: format!(
                "missing name in target '{value}' — expected <kind>:<name>, e.g. dataset:babylm.curation.smoke"
            ),
        },
    })?;
    Ok((RegistryKind::parse(&parsed.kind_str)?, parsed.name))
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
