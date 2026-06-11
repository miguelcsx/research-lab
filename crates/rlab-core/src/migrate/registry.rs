use std::fs;

use serde_json::Value;

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::registry::Registry;

use super::plan::MigrationPlan;
use super::schema::CURRENT_SCHEMA_VERSION;

pub fn validate_registry_cache(registry: &Registry) -> RlabResult<()> {
    registry.validate()
}

pub fn scan_registry_cache_for_migration(
    paths: &ProjectPaths,
    plan: &mut MigrationPlan,
) -> RlabResult<()> {
    if !paths.registry_cache.exists() {
        return Ok(());
    }
    let content = fs::read_to_string(&paths.registry_cache)
        .map_err(|error| RlabError::io(&paths.registry_cache, error))?;
    let value: Value = serde_json::from_str(&content).map_err(RlabError::serialization)?;
    match value.get("schema_version").and_then(Value::as_u64) {
        Some(version) if version == u64::from(CURRENT_SCHEMA_VERSION) => Ok(()),
        Some(version) => {
            let version = u32::try_from(version).map_err(|_| RlabError::Validation {
                message: "registry cache schema_version is too large".to_string(),
            })?;
            plan.push_upgrade(paths.registry_cache.clone(), "registry_cache", version);
            Ok(())
        }
        None => {
            plan.push_missing_schema(paths.registry_cache.clone(), "registry_cache");
            Ok(())
        }
    }
}
