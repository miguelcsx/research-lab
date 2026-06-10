use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, doctor_project, lint_project, load_effective_config, RlabResult,
};

use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct ValidateCommand {
    #[arg(long)]
    pub strict: bool,
}

pub fn run(command: ValidateCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let mut config = load_effective_config(root, &[])?;
    if command.strict {
        config.production.strict = true;
    }
    let paths = ProjectPaths::from_config(&config)?;
    let diagnostics = doctor_project(&config, &paths)?;
    let lint = lint_project(&paths)?;
    let has_error = diagnostics
        .iter()
        .any(|finding| finding.level.as_str() == "error")
        || lint.iter().any(|finding| finding.level == "error");
    let strict_failed = config.production.strict
        && (config.reproducibility.require_lockfile
            && !paths.root.join("uv.lock").exists()
            && !paths.root.join("poetry.lock").exists());
    let valid = !has_error && !strict_failed;
    if json {
        print_json(
            "validate",
            serde_json::json!({
                "schema_version": SCHEMA_VERSION,
                "valid": valid,
                "project": config.project.name,
                "strict": config.production.strict,
                "paths": paths,
                "diagnostics": diagnostics,
                "lint": lint,
            }),
        )?;
    } else if valid {
        print_line("configuration is valid");
    } else {
        print_line("configuration validation failed");
    }
    Ok(if valid { 0 } else { 1 })
}
