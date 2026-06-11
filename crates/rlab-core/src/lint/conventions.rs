use serde::{Deserialize, Serialize};
use walkdir::WalkDir;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LintFinding {
    pub schema_version: u32,
    pub level: String,
    pub message: String,
    pub path: Option<String>,
}

pub fn lint_project(paths: &ProjectPaths) -> RlabResult<Vec<LintFinding>> {
    let mut findings = Vec::new();
    if !paths.root.join("pyproject.toml").exists() && !paths.root.join("lab.toml").exists() {
        findings.push(LintFinding {
            schema_version: SCHEMA_VERSION,
            level: "warning".to_string(),
            message: "project has neither pyproject.toml nor lab.toml".to_string(),
            path: None,
        });
    }
    for entry in WalkDir::new(&paths.root).max_depth(3).into_iter() {
        let entry = entry.map_err(|error| RlabError::Io {
            path: paths.root.clone(),
            message: error.to_string(),
        })?;
        if entry.file_type().is_file() {
            let path = entry.path();
            let metadata = entry.metadata().map_err(|error| RlabError::Io {
                path: path.to_path_buf(),
                message: error.to_string(),
            })?;
            if metadata.len() > 100_000_000 {
                findings.push(LintFinding {
                    schema_version: SCHEMA_VERSION,
                    level: "warning".to_string(),
                    message: "large file should not be committed without intent".to_string(),
                    path: Some(path.display().to_string()),
                });
            }
        }
    }
    Ok(findings)
}
