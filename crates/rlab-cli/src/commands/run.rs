use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use clap::Args;
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, plan_experiment,
    run::list_runs, EffectiveConfig, ExperimentJob, ExperimentSpec, HostCommand, HostEvent,
    HostRequest, HostTarget, ProtocolVersion, RegistryKind, RetryPolicy, RlabError, RlabResult,
    RunDirectory, RunSession, RunStatus,
};
use serde_json::Value;

use crate::commands::discover::discover_registry;
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
    paths.ensure_base_dirs()?;

    let (kind, name) = parse_target_kind(&command.target)?;
    let params = parse_params_public(&command.params)
        .and_then(|params| resolve_param_refs(&paths, params))?;
    let strict = command.strict || config.production.strict;

    let jobs = target_jobs(&config, &paths, strict, &kind, &name)?;
    if jobs.is_empty() {
        let outcome = execute_run(&config, &paths, &kind, &name, params, None, strict)?;
        return report_run(&outcome, json);
    }

    if !json {
        print_line(&format!("sweep: {} jobs", jobs.len()));
    }

    let mut outcomes = Vec::with_capacity(jobs.len());
    for job in &jobs {
        let merged = merge_params(&params, &job.params);
        let outcome = execute_run(&config, &paths, &kind, &name, merged, job.seed, strict)?;

        if !json {
            print_sweep_job_result(job, &outcome);
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
    seed: Option<u64>,
    strict: bool,
) -> RlabResult<RunOutcome> {
    let params = with_seed(params, seed);
    let args = std::env::args().collect();

    let session = RunSession::create(paths, kind.as_str(), name, args, params.clone())?;

    let run_id = session.directory.id.as_str().to_string();

    let request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: run_id.clone(),
        command: HostCommand::Execute,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: Some(HostTarget {
            kind: kind.clone(),
            name: name.to_string(),
        }),
        run_id: Some(run_id),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
        params,
        seed,
        strict,
        environment: Value::Object(serde_json::Map::new()),
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

    let result = match completed {
        Some(result) => result,
        None => empty_result(),
    };

    let run = session.complete(result)?;
    Ok(RunOutcome { run, failed: false })
}

fn empty_result() -> Value {
    serde_json::json!({
        "schema_version": SCHEMA_VERSION,
        "data": {}
    })
}

/// Expand an experiment declaration into matrix × seed jobs.
///
/// A valid cached registry avoids a Python round-trip. If no valid cache exists,
/// discovery runs before planning so an experiment never silently loses its
/// matrix or seeds.
fn target_jobs(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    strict: bool,
    kind: &RegistryKind,
    name: &str,
) -> RlabResult<Vec<ExperimentJob>> {
    if kind != &RegistryKind::EXPERIMENT {
        return Ok(Vec::new());
    }

    let registry = discover_registry(config, paths, strict, false)?;

    let Some(record) = registry.find(kind.clone(), name) else {
        return Ok(Vec::new());
    };

    let matrix = match record.metadata.get("matrix") {
        Some(value) => value.clone(),
        None => Value::Object(serde_json::Map::new()),
    };

    let seeds = match record.metadata.get("seeds") {
        Some(value) => value.clone(),
        None => Value::Array(Vec::new()),
    };

    if value_is_empty_object(&matrix) && value_is_empty_array(&seeds) {
        return Ok(Vec::new());
    }

    let params = match record.metadata.get("params") {
        Some(value) => value.clone(),
        None => Value::Object(serde_json::Map::new()),
    };

    let metrics = match record.metadata.get("metrics") {
        Some(value) => value.clone(),
        None => Value::Array(Vec::new()),
    };

    let spec = ExperimentSpec {
        schema_version: SCHEMA_VERSION,
        name: name.to_string(),
        question: record
            .metadata
            .get("question")
            .and_then(Value::as_str)
            .map(str::to_string),
        hypothesis: record
            .metadata
            .get("hypothesis")
            .and_then(Value::as_str)
            .map(str::to_string),
        params: serde_json::from_value(params).map_err(|error| RlabError::Validation {
            message: format!("invalid experiment params for {name}: {error}"),
        })?,
        matrix: serde_json::from_value(matrix).map_err(|error| RlabError::Validation {
            message: format!("invalid experiment matrix for {name}: {error}"),
        })?,
        metrics: serde_json::from_value(metrics).map_err(|error| RlabError::Validation {
            message: format!("invalid experiment metrics for {name}: {error}"),
        })?,
        seeds: serde_json::from_value(seeds).map_err(|error| RlabError::Validation {
            message: format!("invalid experiment seeds for {name}: {error}"),
        })?,
        retry: RetryPolicy::none(),
    };

    Ok(plan_experiment(&spec)?.jobs)
}

fn value_is_empty_object(value: &Value) -> bool {
    match value.as_object() {
        Some(object) => object.is_empty(),
        None => true,
    }
}

fn value_is_empty_array(value: &Value) -> bool {
    match value.as_array() {
        Some(array) => array.is_empty(),
        None => true,
    }
}

fn merge_params(base: &Value, cell: &std::collections::BTreeMap<String, Value>) -> Value {
    let mut object = serde_json::Map::new();
    object.extend(cell.iter().map(|(k, v)| (k.clone(), v.clone())));
    if let Some(base_obj) = base.as_object() {
        object.extend(base_obj.iter().map(|(k, v)| (k.clone(), v.clone())));
    }
    Value::Object(object)
}

fn with_seed(params: Value, seed: Option<u64>) -> Value {
    let mut object = match params {
        Value::Object(object) => object,
        _ => serde_json::Map::new(),
    };

    if let Some(seed) = seed {
        object.insert("seed".to_string(), Value::from(seed));
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

fn format_job(job: &ExperimentJob) -> String {
    let mut output = String::new();

    for (index, (key, value)) in job.params.iter().enumerate() {
        if index > 0 {
            output.push_str(", ");
        }

        let _ = write!(output, "{key}={value}");
    }

    if let Some(seed) = job.seed {
        if !output.is_empty() {
            output.push_str(", ");
        }

        let _ = write!(output, "seed={seed}");
    }

    output
}

fn print_sweep_job_result(job: &ExperimentJob, outcome: &RunOutcome) {
    let status = if outcome.failed {
        "failed"
    } else {
        "completed"
    };

    print_line(&format!(
        "  {status} {} -> {}",
        format_job(job),
        outcome.run.id.as_str()
    ));
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
            serde_json::json!({
                "runs": ids,
                "failures": failures
            }),
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
        HostEvent::Log(value) | HostEvent::Warning(value) | HostEvent::Error(value) => {
            session.append_log(&value.message)
        }
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
    if looks_like_path(value) {
        return Err(ParseTargetError::FilePath {
            value: value.to_string(),
        });
    }

    let Some((kind_str, name)) = value.split_once(':') else {
        return match default_kind {
            Some(kind) => Ok(ParsedTarget {
                kind_str: kind.to_string(),
                name: value.to_string(),
            }),
            None => Err(ParseTargetError::InvalidKind {
                value: value.to_string(),
                reason: "expected <kind>:<name>".to_string(),
            }),
        };
    };

    if kind_str.trim().is_empty() {
        return Err(ParseTargetError::InvalidKind {
            value: value.to_string(),
            reason: "expected <kind>:<name>".to_string(),
        });
    }

    if name.trim().is_empty() {
        return Err(ParseTargetError::MissingName {
            value: value.to_string(),
        });
    }

    Ok(ParsedTarget {
        kind_str: kind_str.to_string(),
        name: name.to_string(),
    })
}

fn looks_like_path(value: &str) -> bool {
    value.ends_with(".py")
        || value.ends_with(".toml")
        || value.starts_with('/')
        || value.starts_with("./")
        || value.starts_with("../")
        || value.starts_with('\\')
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
        let Some((key, raw_value)) = param.split_once('=') else {
            return Err(RlabError::Validation {
                message: format!("parameter must be key=value: {param}"),
            });
        };

        if key.trim().is_empty() {
            return Err(RlabError::Validation {
                message: format!("invalid parameter: {param}"),
            });
        }

        object.insert(key.to_string(), parse_param_value(raw_value));
    }

    Ok(serde_json::Value::Object(object))
}

fn parse_param_value(value: &str) -> serde_json::Value {
    match serde_json::from_str(value) {
        Ok(parsed) => parsed,
        Err(_) => serde_json::Value::String(value.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use serde_json::json;

    use super::{merge_params, parse_param_value, with_seed};

    #[test]
    fn explicit_params_override_matrix_values() {
        let cell = BTreeMap::from([
            ("batch_size".to_string(), json!(16)),
            ("embedding".to_string(), json!("euclidean")),
        ]);

        let merged = merge_params(&json!({"batch_size": 32}), &cell);

        assert_eq!(merged["batch_size"], json!(32));
        assert_eq!(merged["embedding"], json!("euclidean"));
    }

    #[test]
    fn seed_is_recorded_in_job_params() {
        let params = with_seed(json!({"batch_size": 32}), Some(7));

        assert_eq!(params["seed"], json!(7));
        assert_eq!(params["batch_size"], json!(32));
    }

    #[test]
    fn explicit_params_accept_structured_json() {
        assert_eq!(parse_param_value("[]"), json!([]));
        assert_eq!(
            parse_param_value(r#"{"warmup":0.1}"#),
            json!({"warmup": 0.1})
        );
        assert_eq!(parse_param_value("causal"), json!("causal"));
    }
}
