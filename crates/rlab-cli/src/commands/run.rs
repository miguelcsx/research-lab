use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use clap::Args;
use rlab_core::{
    config::ProjectPaths, load_effective_config, plan_record_experiment, run::list_runs,
    EffectiveConfig, ExperimentJob, HostEvent, Registry, RegistryKind, RlabError, RlabResult,
    RunDirectory, RunSession, RunStatus,
};
use serde_json::Value;

use crate::commands::discover::discover_registry;
use crate::host::execution::{self, ExecutionRequest};
use crate::render::{human::print_line, json::print_json};

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct RunCommand {
    pub target: String,

    #[arg(long)]
    pub strict: bool,

    #[arg(long = "param", alias = "params")]
    pub params: Vec<String>,
}

pub(crate) struct RunOutcome {
    pub(crate) run: RunDirectory,
    pub(crate) failed: bool,
}

pub fn run(command: RunCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;

    let strict = command.strict || config.production.strict;
    let (kind, name) = resolve_run_target(&config, &paths, strict, &command.target)?;
    let params = parse_params_public(&command.params)
        .and_then(|params| resolve_param_refs(&paths, params))?;

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
pub(crate) fn execute_run(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    kind: &RegistryKind,
    name: &str,
    params: Value,
    seed: Option<u64>,
    strict: bool,
) -> RlabResult<RunOutcome> {
    let outcome = execution::execute_run(ExecutionRequest {
        config,
        paths,
        operation: kind.as_str(),
        name,
        target_kind: kind.clone(),
        target_name: name,
        params,
        seed,
        strict,
        default_result: empty_result(),
    })?;
    Ok(RunOutcome {
        run: outcome.run,
        failed: outcome.failed,
    })
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
pub(crate) fn target_jobs(
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

    plan_record_experiment(record)
}

pub(crate) fn merge_params(
    base: &Value,
    cell: &std::collections::BTreeMap<String, Value>,
) -> Value {
    let mut object = serde_json::Map::new();
    object.extend(cell.iter().map(|(k, v)| (k.clone(), v.clone())));
    if let Some(base_obj) = base.as_object() {
        object.extend(base_obj.iter().map(|(k, v)| (k.clone(), v.clone())));
    }
    Value::Object(object)
}

/// Resolve `@<kind>:<name>[/suffix]` param values to the latest completed run's
/// output path, so pipeline stages reference each other without pasting run ids.
pub(crate) fn resolve_param_refs(paths: &ProjectPaths, params: Value) -> RlabResult<Value> {
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
    execution::process_event(session, event, completed, failed)
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

fn resolve_run_target(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    strict: bool,
    value: &str,
) -> RlabResult<(RegistryKind, String)> {
    if value.contains(':') || looks_like_path(value) {
        return parse_target_kind(value);
    }

    let registry = discover_registry(config, paths, strict, false)?;
    match unique_bare_target(&registry, value)? {
        Some(target) => Ok(target),
        None => Err(RlabError::Reference {
            message: format!(
                "no registry target named '{value}' — use <kind>:<name> or run 'rlab discover'"
            ),
        }),
    }
}

fn unique_bare_target(
    registry: &Registry,
    name: &str,
) -> RlabResult<Option<(RegistryKind, String)>> {
    let matches = registry
        .records
        .iter()
        .filter(|record| record.name == name)
        .map(|record| (record.kind.clone(), record.name.clone()))
        .collect::<Vec<_>>();

    match matches.as_slice() {
        [] => Ok(None),
        [(kind, name)] => Ok(Some((kind.clone(), name.clone()))),
        _ => Err(RlabError::Reference {
            message: format!(
                "ambiguous target '{name}' — use one of: {}",
                matches
                    .iter()
                    .map(|(kind, name)| format!("{}:{name}", kind.as_str()))
                    .collect::<Vec<_>>()
                    .join(", ")
            ),
        }),
    }
}

pub fn parse_params_public(params: &[String]) -> RlabResult<serde_json::Value> {
    let mut object = serde_json::Map::new();

    for param in params {
        let Some((key, raw_value)) = param.split_once('=') else {
            merge_json_params(&mut object, param)?;
            continue;
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

fn merge_json_params(
    object: &mut serde_json::Map<String, serde_json::Value>,
    raw: &str,
) -> RlabResult<()> {
    match serde_json::from_str::<serde_json::Value>(raw) {
        Ok(serde_json::Value::Object(values)) => {
            object.extend(values);
            Ok(())
        }
        Ok(_) => Err(RlabError::Validation {
            message: format!("parameter JSON must be an object: {raw}"),
        }),
        Err(_) => Err(RlabError::Validation {
            message: format!("parameter must be key=value or a JSON object: {raw}"),
        }),
    }
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
    use std::path::PathBuf;

    use serde_json::json;

    use rlab_core::{Registry, RegistryKind, RegistryRecord, RegistryRecordSpec};

    use crate::host::execution::with_seed;

    use super::{merge_params, parse_param_value, parse_params_public, unique_bare_target};

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

    #[test]
    fn explicit_params_accept_json_object() {
        assert_eq!(
            parse_params_public(&[r#"{"config":"ablation","seed":7}"#.to_string()]).unwrap(),
            json!({"config": "ablation", "seed": 7})
        );
    }

    #[test]
    fn bare_target_resolves_when_unique() {
        let registry = registry_with([
            (RegistryKind::WORKFLOW, "training.compile_plan"),
            (RegistryKind::DATASET, "babylm.curation.smoke"),
        ]);

        let (kind, name) = unique_bare_target(&registry, "training.compile_plan")
            .unwrap()
            .unwrap();

        assert_eq!(kind, RegistryKind::WORKFLOW);
        assert_eq!(name, "training.compile_plan");
    }

    #[test]
    fn bare_target_rejects_ambiguous_names() {
        let registry = registry_with([
            (RegistryKind::WORKFLOW, "smoke"),
            (RegistryKind::DATASET, "smoke"),
        ]);

        let error = unique_bare_target(&registry, "smoke").unwrap_err();

        assert!(error.to_string().contains("ambiguous target"));
    }

    fn registry_with<const N: usize>(records: [(RegistryKind, &str); N]) -> Registry {
        let mut registry = Registry::new();
        for (kind, name) in records {
            registry.insert(record(kind, name)).unwrap();
        }
        registry
    }

    fn record(kind: RegistryKind, name: &str) -> RegistryRecord {
        RegistryRecord::from_spec(RegistryRecordSpec {
            kind,
            name: name.to_string(),
            version: "1".to_string(),
            module: "tests".to_string(),
            qualname: name.to_string(),
            source: PathBuf::from("tests.py"),
            tags: Vec::new(),
            description: String::new(),
            metadata: BTreeMap::new(),
        })
    }
}
