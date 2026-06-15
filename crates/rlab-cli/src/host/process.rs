use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};

use rlab_core::{HostEvent, HostRequest, RlabError, RlabResult};

pub fn run_python_host(
    python: &str,
    runner_module: &str,
    request: &HostRequest,
) -> RlabResult<Vec<HostEvent>> {
    let python = resolve_program(&request.project_root, python);
    let mut child = Command::new(&python)
        .arg("-m")
        .arg(runner_module)
        .current_dir(&request.project_root)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| RlabError::Host {
            message: format!("failed to start Python runner {runner_module}: {error}"),
        })?;
    let request_line = serde_json::to_string(request).map_err(RlabError::serialization)?;
    match child.stdin.as_mut() {
        Some(stdin) => {
            stdin
                .write_all(request_line.as_bytes())
                .map_err(|error| RlabError::Host {
                    message: format!("failed to write runner request: {error}"),
                })?;
            stdin.write_all(b"\n").map_err(|error| RlabError::Host {
                message: format!("failed to finish runner request: {error}"),
            })?;
        }
        None => {
            return Err(RlabError::Host {
                message: "Python runner stdin unavailable".to_string(),
            })
        }
    }
    let output = child.wait_with_output().map_err(|error| RlabError::Host {
        message: format!("failed to wait for Python runner: {error}"),
    })?;
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        return Err(RlabError::Host {
            message: format!("Python runner failed: {stderr}"),
        });
    }
    let stdout = String::from_utf8(output.stdout).map_err(RlabError::serialization)?;
    let mut events = Vec::new();
    for line in stdout.lines().filter(|line| !line.trim().is_empty()) {
        let event: HostEvent = serde_json::from_str(line).map_err(RlabError::serialization)?;
        events.push(event);
    }
    Ok(events)
}

fn resolve_program(project_root: &Path, program: &str) -> PathBuf {
    let path = PathBuf::from(program);
    if path.is_absolute() || path.components().count() == 1 {
        path
    } else {
        project_root.join(path)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn leaves_path_lookup_programs_unqualified() {
        assert_eq!(
            resolve_program(Path::new("/repo"), "python"),
            PathBuf::from("python")
        );
    }

    #[test]
    fn resolves_relative_paths_from_project_root() {
        assert_eq!(
            resolve_program(Path::new("/repo"), ".venv/bin/python"),
            PathBuf::from("/repo/.venv/bin/python")
        );
    }
}
