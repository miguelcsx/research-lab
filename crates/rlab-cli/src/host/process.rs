use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::thread;

use rlab_core::{HostEvent, HostRequest, RlabError, RlabResult};

use crate::logger;

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
    if let Some(stdin) = child.stdin.as_mut() {
        stdin
            .write_all(request_line.as_bytes())
            .map_err(|error| RlabError::Host {
                message: format!("failed to write runner request: {error}"),
            })?;
        stdin.write_all(b"\n").map_err(|error| RlabError::Host {
            message: format!("failed to finish runner request: {error}"),
        })?;
    }
    drop(child.stdin.take());

    let stdout = child.stdout.take().ok_or_else(|| RlabError::Host {
        message: "Python runner stdout unavailable".to_string(),
    })?;
    let events_handle = thread::spawn(move || -> RlabResult<Vec<HostEvent>> {
        let reader = BufReader::new(stdout);
        let mut events = Vec::new();
        for line in reader.lines() {
            let line = line.map_err(|error| RlabError::Host {
                message: format!("failed to read runner output: {error}"),
            })?;
            if line.trim().is_empty() {
                continue;
            }
            let event = parse_host_event_line(&line)?;
            logger::event(&event);
            events.push(event);
        }
        Ok(events)
    });

    let stderr = child.stderr.take().ok_or_else(|| RlabError::Host {
        message: "Python runner stderr unavailable".to_string(),
    })?;
    let stderr_handle = thread::spawn(move || -> RlabResult<Vec<String>> {
        let reader = BufReader::new(stderr);
        let mut lines = Vec::new();
        for line in reader.lines() {
            let line = line.map_err(|error| RlabError::Host {
                message: format!("failed to read runner stderr: {error}"),
            })?;
            lines.push(line);
        }
        Ok(lines)
    });

    let status = child.wait().map_err(|error| RlabError::Host {
        message: format!("failed to wait for Python runner: {error}"),
    })?;

    let events = events_handle
        .join()
        .map_err(|_| RlabError::Host {
            message: "stdout reader thread panicked".to_string(),
        })?
        .map_err(|error| RlabError::Host {
            message: format!("stdout reader failed: {error}"),
        })?;
    let stderr_lines = stderr_handle
        .join()
        .map_err(|_| RlabError::Host {
            message: "stderr reader thread panicked".to_string(),
        })?
        .map_err(|error| RlabError::Host {
            message: format!("stderr reader failed: {error}"),
        })?;

    if !status.success() {
        return Err(RlabError::Host {
            message: format!("Python runner failed: {}", stderr_lines.join("\n")),
        });
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

fn parse_host_event_line(line: &str) -> RlabResult<HostEvent> {
    serde_json::from_str(line).map_err(|error| RlabError::Host {
        message: format!(
            "Python runner wrote non-protocol stdout; stdout is reserved for rlab host events. line={} error={error}",
            preview(line),
        ),
    })
}

fn preview(line: &str) -> String {
    const LIMIT: usize = 120;
    let mut value: String = line.chars().take(LIMIT).collect();
    if line.chars().count() > LIMIT {
        value.push_str("...");
    }
    value
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

    #[test]
    fn previews_long_stdout_lines() {
        let line = "x".repeat(130);
        assert_eq!(preview(&line), format!("{}...", "x".repeat(120)));
    }

    #[test]
    fn non_protocol_stdout_names_reserved_stdout() {
        let error = parse_host_event_line("plain print").unwrap_err();
        assert!(error.to_string().contains("stdout is reserved"));
        assert!(error.to_string().contains("plain print"));
    }
}
