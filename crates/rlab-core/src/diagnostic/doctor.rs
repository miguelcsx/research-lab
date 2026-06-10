use crate::config::{EffectiveConfig, ProjectPaths};
use crate::error::RlabResult;

use super::finding::{DiagnosticFinding, DiagnosticLevel};

pub fn doctor_project(config: &EffectiveConfig, paths: &ProjectPaths) -> RlabResult<Vec<DiagnosticFinding>> {
    let mut findings = Vec::new();
    if !config.project.root.join("lab.toml").exists() {
        findings.push(DiagnosticFinding {
            level: DiagnosticLevel::Info,
            code: "zero_config".to_string(),
            message: "lab.toml not found; using zero-config defaults".to_string(),
        });
    }
    if config.python.modules.is_empty() {
        findings.push(DiagnosticFinding {
            level: DiagnosticLevel::Warning,
            code: "no_modules".to_string(),
            message: "no Python modules configured or inferred".to_string(),
        });
    }
    if !paths.cache.exists() {
        findings.push(DiagnosticFinding {
            level: DiagnosticLevel::Info,
            code: "cache_missing".to_string(),
            message: "cache directory will be created when needed".to_string(),
        });
    }
    Ok(findings)
}
