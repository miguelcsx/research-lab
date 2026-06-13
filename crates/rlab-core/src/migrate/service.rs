use crate::config::ProjectPaths;
use crate::error::RlabResult;

use super::plan::MigrationPlan;

pub fn migration_status() -> MigrationPlan {
    MigrationPlan::empty()
}

pub fn migration_plan(paths: &ProjectPaths) -> RlabResult<MigrationPlan> {
    let mut plan = MigrationPlan::empty();
    super::runs::scan_runs_for_migration(paths, &mut plan)?;
    super::registry::scan_registry_cache_for_migration(paths, &mut plan)?;
    Ok(plan)
}
