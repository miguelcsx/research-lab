use std::collections::BTreeMap;
use std::fs;

use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LabPolicy {
    pub schema_version: u32,
    pub require_hypothesis: bool,
    pub require_data_manifest: bool,
    pub require_clean_git_for_promotion: bool,
    pub require_review_for_paper: bool,
    pub forbidden_env_patterns: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PolicyViolation {
    pub rule: String,
    pub subject: String,
}

impl LabPolicy {
    pub fn load(paths: &ProjectPaths) -> RlabResult<Self> {
        let path = paths.root.join("lab.policy.toml");
        if !path.exists() {
            return Ok(Self::default_policy());
        }
        let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
        toml::from_str(&content).map_err(RlabError::serialization)
    }

    pub fn default_policy() -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            require_hypothesis: false,
            require_data_manifest: false,
            require_clean_git_for_promotion: false,
            require_review_for_paper: false,
            forbidden_env_patterns: vec!["TOKEN".to_string(), "SECRET".to_string(), "PASSWORD".to_string(), "KEY".to_string()],
        }
    }

    pub fn check_env(&self, env: &BTreeMap<String, String>) -> Vec<PolicyViolation> {
        env.keys()
            .filter(|key| {
                let upper = key.to_uppercase();
                self.forbidden_env_patterns.iter().any(|pattern| upper.contains(&pattern.to_uppercase()))
            })
            .map(|key| PolicyViolation { rule: "forbidden_env_patterns".to_string(), subject: key.clone() })
            .collect()
    }
}
