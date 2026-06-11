use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::error::{RlabError, RlabResult};

use super::schema::CURRENT_SCHEMA_VERSION;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationAction {
    pub path: PathBuf,
    pub action: String,
    pub from_schema_version: Option<u32>,
    pub to_schema_version: u32,
    pub reason: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MigrationPlan {
    pub schema_version: u32,
    pub current_schema_version: u32,
    pub actions: Vec<MigrationAction>,
}

impl MigrationPlan {
    pub fn empty() -> Self {
        Self {
            schema_version: CURRENT_SCHEMA_VERSION,
            current_schema_version: CURRENT_SCHEMA_VERSION,
            actions: Vec::new(),
        }
    }

    pub fn push_missing_schema(&mut self, path: PathBuf, kind: &str) {
        self.actions.push(MigrationAction {
            path,
            action: "add_schema_version".to_string(),
            from_schema_version: None,
            to_schema_version: CURRENT_SCHEMA_VERSION,
            reason: format!("{kind} file is missing schema_version"),
        });
    }

    pub fn push_upgrade(&mut self, path: PathBuf, kind: &str, from: u32) {
        self.actions.push(MigrationAction {
            path,
            action: "upgrade_schema".to_string(),
            from_schema_version: Some(from),
            to_schema_version: CURRENT_SCHEMA_VERSION,
            reason: format!(
                "{kind} file schema_version {from} is older than {CURRENT_SCHEMA_VERSION}"
            ),
        });
    }

    pub fn ensure_supported(&self) -> RlabResult<()> {
        for action in &self.actions {
            if action.from_schema_version.is_none() {
                return Err(RlabError::Validation {
                    message: format!(
                        "cannot automatically migrate file without schema_version: {}",
                        action.path.display()
                    ),
                });
            }
        }
        Ok(())
    }
}
