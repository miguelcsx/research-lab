use std::process::Command;

use serde_json::json;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::{write_json_atomic, write_text_atomic};
use crate::run::RunDirectory;
const SCHEMA_VERSION: u32 = 1;

pub fn capture_reproducibility(paths: &ProjectPaths, run: &RunDirectory) -> RlabResult<()> {
    let dir = run.path.join("reproducibility");
    write_text_atomic(&dir.join("command.txt"), &run.command.join(" "))?;
    write_json_atomic(&dir.join("env.json"), &environment_capture())?;
    write_json_atomic(&dir.join("git.json"), &git_capture(&paths.root)?)?;
    if let Some(diff) = git_diff(&paths.root)? {
        write_text_atomic(&dir.join("git.diff"), &diff)?;
    }
    copy_if_present(paths, &dir, "pyproject.toml")?;
    copy_if_present(paths, &dir, "uv.lock")?;
    copy_if_present(paths, &dir, "lab.toml")?;
    write_text_atomic(&dir.join("lockfile"), &lockfile_marker(paths))?;
    Ok(())
}

fn copy_if_present(paths: &ProjectPaths, dir: &std::path::Path, name: &str) -> RlabResult<()> {
    let source = paths.root.join(name);
    if source.exists() {
        let target = dir.join(name);
        std::fs::copy(&source, &target).map_err(|error| RlabError::io(&target, error))?;
    }
    Ok(())
}

fn lockfile_marker(paths: &ProjectPaths) -> String {
    let lockfiles = ["uv.lock", "poetry.lock", "Pipfile.lock", "Cargo.lock"];
    let present = lockfiles
        .iter()
        .filter(|name| paths.root.join(name).exists())
        .copied()
        .collect::<Vec<_>>();
    if present.is_empty() {
        "no lockfile captured\n".to_string()
    } else {
        format!("captured lockfiles: {}\n", present.join(", "))
    }
}

fn environment_capture() -> serde_json::Value {
    json!({
        "schema_version": SCHEMA_VERSION,
        "os": std::env::consts::OS,
        "arch": std::env::consts::ARCH,
        "current_exe": std::env::current_exe().ok().map(|path| path.display().to_string())
    })
}

fn git_capture(root: &std::path::Path) -> RlabResult<serde_json::Value> {
    let commit = run_git(root, &["rev-parse", "HEAD"])?;
    let branch = run_git(root, &["rev-parse", "--abbrev-ref", "HEAD"])?;
    let status = run_git(root, &["status", "--porcelain"])?;
    Ok(json!({
        "schema_version": SCHEMA_VERSION,
        "commit": commit.map(|value| value.trim().to_string()),
        "branch": branch.map(|value| value.trim().to_string()),
        "dirty": status.as_ref().map(|value| !value.trim().is_empty())
    }))
}

fn git_diff(root: &std::path::Path) -> RlabResult<Option<String>> {
    run_git(root, &["diff"])
}

fn run_git(root: &std::path::Path, args: &[&str]) -> RlabResult<Option<String>> {
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
