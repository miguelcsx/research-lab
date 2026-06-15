use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RegistryKind, RlabResult};

use crate::commands::run::{parse_params_public, parse_target, ParseTargetError, ParsedTarget};
use crate::host::execution::{self, ExecutionRequest};
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
    #[arg(long = "param", alias = "params")]
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
    let outcome = execution::execute_run(ExecutionRequest {
        config: &config,
        paths: &paths,
        operation: RegistryKind::BENCHMARK.as_str(),
        name: &command.benchmark_name,
        target_kind: RegistryKind::BENCHMARK,
        target_name: &command.benchmark_name,
        params,
        seed: None,
        strict: command.strict,
        default_result: serde_json::json!({"schema_version": SCHEMA_VERSION, "data": {}}),
    })?;
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
