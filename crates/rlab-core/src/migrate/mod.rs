pub mod plan;
pub mod registry;
pub mod runs;
pub mod schema;

use crate::config::ProjectPaths;
use crate::error::RlabResult;

pub use plan::{MigrationAction, MigrationPlan};
pub use schema::CURRENT_SCHEMA_VERSION;

pub fn migration_status() -> MigrationPlan {
    MigrationPlan::empty()
}

pub fn migration_plan(paths: &ProjectPaths) -> RlabResult<MigrationPlan> {
    let mut plan = MigrationPlan::empty();
    runs::scan_runs_for_migration(paths, &mut plan)?;
    registry::scan_registry_cache_for_migration(paths, &mut plan)?;
    Ok(plan)
}
