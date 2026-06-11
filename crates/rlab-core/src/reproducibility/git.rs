use std::path::Path;
use std::process::Command;

use serde_json::{json, Value};

use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

pub fn capture_git(root: &Path) -> RlabResult<Value> {
    let commit = run_git(root, &["rev-parse", "HEAD"])?;
    let branch = run_git(root, &["rev-parse", "--abbrev-ref", "HEAD"])?;
    let status = run_git(root, &["status", "--porcelain"])?;
    Ok(json!({
        "schema_version": SCHEMA_VERSION,
        "commit": commit.map(|value| value.trim().to_string()),
        "branch": branch.map(|value| value.trim().to_string()),
        "dirty": status.as_ref().map(|value| !value.trim().is_empty()),
    }))
}

pub fn capture_git_diff(root: &Path) -> RlabResult<Option<String>> {
    run_git(root, &["diff"])
}

fn run_git(root: &Path, args: &[&str]) -> RlabResult<Option<String>> {
    let output = Command::new("git").args(args).current_dir(root).output();
    match output {
        Ok(value) if value.status.success() => String::from_utf8(value.stdout)
            .map(Some)
            .map_err(RlabError::serialization),
        Ok(_) => Ok(None),
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(error) => Err(RlabError::io(root, error)),
    }
}
