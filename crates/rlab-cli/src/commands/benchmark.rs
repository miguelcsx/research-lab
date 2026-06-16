use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RegistryKind, RlabError, RlabResult};
use serde_json::Value;

use crate::commands::discover::discover_registry;
use crate::commands::records_targeting;
use crate::commands::run::{parse_params_public, parse_target, ParseTargetError, ParsedTarget};
use crate::host::execution::{self, ExecutionRequest};
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct BenchmarkCommand {
    /// Benchmark id or target id. Forms: `rlab benchmark <benchmark-id> <target-id>` or `rlab benchmark <target-id>`.
    pub benchmark_or_target: String,
    /// Target to benchmark. Accepts a bare name (resolved as `model:<name>`),
    /// `<kind>:<name>` (e.g. `model:foo.bar`), or `<kind>:<loader>:<path>`
    /// (e.g. `model:hf:org/repo`).
    pub target: Option<String>,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param", alias = "params")]
    pub params: Vec<String>,
}

pub fn run(command: BenchmarkCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;
    let strict = command.strict || config.production.strict;
    let params = parse_params_public(&command.params)?;
    if command.target.is_none() && command.benchmark_or_target.contains(':') {
        let registry = discover_registry(&config, &paths, strict, false)?;
        let benchmarks = records_targeting(
            &registry.records,
            RegistryKind::BENCHMARK,
            &command.benchmark_or_target,
        );
        if benchmarks.is_empty() {
            return Err(RlabError::validation(format!(
                "no benchmarks target {}",
                command.benchmark_or_target
            )));
        }
        let mut runs = Vec::with_capacity(benchmarks.len());
        let mut failures = 0usize;
        for benchmark in benchmarks {
            let outcome = execute_benchmark(
                &config,
                &paths,
                benchmark.name.as_str(),
                &command.benchmark_or_target,
                params.clone(),
                strict,
            )?;
            failures += usize::from(outcome.failed);
            runs.push(outcome.run.id);
        }
        if json {
            print_json(
                "benchmark",
                serde_json::json!({"runs": runs, "failures": failures}),
            )?;
        } else {
            print_line(&format!(
                "benchmarks complete: {} runs, {} failed",
                runs.len(),
                failures
            ));
        }
        return Ok(u8::from(failures > 0));
    }

    let target = command
        .target
        .as_deref()
        .ok_or_else(|| RlabError::validation("benchmark target is required"))?;
    let parsed = parse_target(target, Some("model")).map_err(|error| match error {
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
    let outcome = execute_benchmark(
        &config,
        &paths,
        &command.benchmark_or_target,
        &format!("{kind_str}:{name}"),
        params,
        strict,
    )?;
    if json {
        print_json("benchmark", &outcome.run)?;
    } else if outcome.failed {
        print_line(&format!("benchmark failed: {}", outcome.run.id.as_str()));
    } else {
        print_line(&format!(
            "completed benchmark run: {}",
            outcome.run.id.as_str()
        ));
    }
    Ok(u8::from(outcome.failed))
}

fn execute_benchmark(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    benchmark: &str,
    target: &str,
    params: Value,
    strict: bool,
) -> RlabResult<execution::ExecutionOutcome> {
    execution::execute_run(ExecutionRequest {
        config,
        paths,
        operation: RegistryKind::BENCHMARK.as_str(),
        name: benchmark,
        target_kind: RegistryKind::BENCHMARK,
        target_name: benchmark,
        params: benchmark_params(params, target),
        seed: None,
        strict,
        default_result: serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}),
    })
}

fn benchmark_params(mut params: Value, target: &str) -> Value {
    if let Value::Object(object) = &mut params {
        object.insert("target".to_string(), Value::String(target.to_string()));
    }
    params
}
