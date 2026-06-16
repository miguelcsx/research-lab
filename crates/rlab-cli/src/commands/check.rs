use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RegistryKind, RlabError, RlabResult};
use serde_json::Value;

use crate::commands::discover::discover_registry;
use crate::commands::records_targeting;
use crate::commands::run::{execute_run, parse_params_public};
use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct CheckCommand {
    /// Check id or target id. Forms: `rlab check <check-id> <target-id>` or `rlab check <target-id>`.
    pub check_or_target: String,
    /// Target id for explicit checks, for example `attention:sdpa`.
    pub target: Option<String>,
    #[arg(long)]
    pub strict: bool,
    #[arg(long = "param", alias = "params")]
    pub params: Vec<String>,
}

pub fn run(command: CheckCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;
    let strict = command.strict || config.production.strict;
    let params = parse_params_public(&command.params)?;
    if command.target.is_none() && command.check_or_target.contains(':') {
        let registry = discover_registry(&config, &paths, strict, false)?;
        let checks = records_targeting(
            &registry.records,
            RegistryKind::CHECK,
            &command.check_or_target,
        );
        if checks.is_empty() {
            return Err(RlabError::validation(format!(
                "no checks target {}",
                command.check_or_target
            )));
        }
        let mut runs = Vec::with_capacity(checks.len());
        let mut failures = 0usize;
        for check in checks {
            let outcome = execute_check(
                &config,
                &paths,
                check.name.as_str(),
                &command.check_or_target,
                params.clone(),
                strict,
            )?;
            failures += usize::from(outcome.failed);
            runs.push(outcome.run.id);
        }
        if json {
            print_json(
                "check",
                serde_json::json!({"runs": runs, "failures": failures}),
            )?;
        } else {
            print_line(&format!(
                "checks complete: {} runs, {} failed",
                runs.len(),
                failures
            ));
        }
        return Ok(u8::from(failures > 0));
    }

    let target = command.target.as_deref().unwrap_or("");
    let outcome = execute_run(
        &config,
        &paths,
        &RegistryKind::CHECK,
        &command.check_or_target,
        check_params(params, target),
        None,
        strict,
    )?;
    if json {
        print_json("check", &outcome.run)?;
    } else if outcome.failed {
        print_line(&format!("check failed: {}", outcome.run.id.as_str()));
    } else {
        print_line(&format!("completed check: {}", outcome.run.id.as_str()));
    }
    Ok(u8::from(outcome.failed))
}

fn execute_check(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    check: &str,
    target: &str,
    params: Value,
    strict: bool,
) -> RlabResult<crate::commands::run::RunOutcome> {
    execute_run(
        config,
        paths,
        &RegistryKind::CHECK,
        check,
        check_params(params, target),
        None,
        strict,
    )
}

fn check_params(mut params: Value, target: &str) -> Value {
    if !target.is_empty() {
        if let Value::Object(object) = &mut params {
            object.insert(
                "check_target".to_string(),
                Value::String(target.to_string()),
            );
        }
    }
    params
}
