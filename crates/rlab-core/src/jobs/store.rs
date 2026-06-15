use std::process::Command;

use serde::{Deserialize, Serialize};
use time::OffsetDateTime;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::write_text_atomic;
use crate::journal::append::{append_jsonl, read_jsonl};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum JobStatus {
    Running,
    Completed,
    Failed,
    Cancelled,
}

impl JobStatus {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Running => "running",
            Self::Completed => "completed",
            Self::Failed => "failed",
            Self::Cancelled => "cancelled",
        }
    }

    pub fn parse(value: &str) -> RlabResult<Self> {
        match value {
            "running" => Ok(Self::Running),
            "completed" => Ok(Self::Completed),
            "failed" => Ok(Self::Failed),
            "cancelled" => Ok(Self::Cancelled),
            _ => Err(RlabError::Validation {
                message: format!("unknown job status: {value}"),
            }),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JobRecord {
    pub schema_version: u32,
    pub id: String,
    pub command: String,
    pub status: JobStatus,
    pub exit_code: Option<i32>,
    pub log_path: String,
    #[serde(with = "time::serde::rfc3339")]
    pub created_at: OffsetDateTime,
    #[serde(default, with = "time::serde::rfc3339::option")]
    pub completed_at: Option<OffsetDateTime>,
}

impl JobRecord {
    pub fn new(
        id: String,
        command: String,
        status: JobStatus,
        log_path: String,
        exit_code: Option<i32>,
    ) -> RlabResult<Self> {
        validate_nonempty("job id", &id)?;
        validate_command(&command)?;
        validate_nonempty("job log path", &log_path)?;
        let now = OffsetDateTime::now_utc();
        Ok(Self {
            schema_version: SCHEMA_VERSION,
            id,
            command,
            status,
            exit_code,
            log_path,
            created_at: now,
            completed_at: match status {
                JobStatus::Running => None,
                _ => Some(now),
            },
        })
    }
}

pub fn start_job(paths: &ProjectPaths, command: &str) -> RlabResult<JobRecord> {
    validate_command(command)?;
    let id = format!("job_{}", OffsetDateTime::now_utc().unix_timestamp_nanos());
    let log_path = paths.cache.join("jobs").join(format!("{id}.log"));
    let started_at = OffsetDateTime::now_utc();
    let output = if cfg!(target_os = "windows") {
        Command::new("cmd").args(["/C", command]).output()
    } else {
        Command::new("sh").args(["-c", command]).output()
    }
    .map_err(|error| RlabError::Io {
        path: paths.root.clone(),
        message: error.to_string(),
    })?;
    let mut log = String::new();
    log.push_str(&String::from_utf8_lossy(&output.stdout));
    log.push_str(&String::from_utf8_lossy(&output.stderr));
    write_text_atomic(&log_path, &log)?;
    let status = if output.status.success() {
        JobStatus::Completed
    } else {
        JobStatus::Failed
    };
    let record = JobRecord {
        schema_version: SCHEMA_VERSION,
        id,
        command: command.to_string(),
        status,
        exit_code: output.status.code(),
        log_path: log_path.display().to_string(),
        created_at: started_at,
        completed_at: Some(OffsetDateTime::now_utc()),
    };
    append_jsonl(&paths.cache.join("jobs.jsonl"), &record)?;
    Ok(record)
}

pub fn list_jobs(paths: &ProjectPaths) -> RlabResult<Vec<JobRecord>> {
    read_jsonl(&paths.cache.join("jobs.jsonl"))
}

pub fn job_logs(paths: &ProjectPaths, id: &str) -> RlabResult<String> {
    let jobs = list_jobs(paths)?;
    let record = jobs
        .into_iter()
        .rev()
        .find(|job| job.id == id)
        .ok_or_else(|| RlabError::NotFound {
            subject: format!("job {id}"),
        })?;
    std::fs::read_to_string(&record.log_path).map_err(|error| RlabError::Io {
        path: record.log_path.into(),
        message: error.to_string(),
    })
}

pub fn cancel_job(paths: &ProjectPaths, id: &str) -> RlabResult<JobRecord> {
    let jobs = list_jobs(paths)?;
    let latest = jobs
        .iter()
        .rev()
        .find(|job| job.id == id)
        .ok_or_else(|| RlabError::NotFound {
            subject: format!("job {id}"),
        })?;
    if latest.status != JobStatus::Running {
        return Err(RlabError::Validation {
            message: format!("job {id} is not running and cannot be cancelled"),
        });
    }
    let record = JobRecord {
        schema_version: SCHEMA_VERSION,
        id: id.to_string(),
        command: latest.command.clone(),
        status: JobStatus::Cancelled,
        exit_code: None,
        log_path: latest.log_path.clone(),
        created_at: latest.created_at,
        completed_at: Some(OffsetDateTime::now_utc()),
    };
    append_jsonl(&paths.cache.join("jobs.jsonl"), &record)?;
    Ok(record)
}

fn validate_command(command: &str) -> RlabResult<()> {
    if command.trim().is_empty() {
        return Err(RlabError::Validation {
            message: "job command cannot be empty".to_string(),
        });
    }
    Ok(())
}

fn validate_nonempty(label: &str, value: &str) -> RlabResult<()> {
    if value.trim().is_empty() {
        return Err(RlabError::Validation {
            message: format!("{label} cannot be empty"),
        });
    }
    Ok(())
}
