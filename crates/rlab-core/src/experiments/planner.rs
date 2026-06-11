use crate::error::RlabResult;

use super::matrix::Grid;
use super::model::{ExperimentJob, ExperimentPlan, ExperimentSpec};
const SCHEMA_VERSION: u32 = 1;

pub fn plan_experiment(spec: &ExperimentSpec) -> RlabResult<ExperimentPlan> {
    spec.validate()?;
    let grid = Grid::new(spec.matrix.clone())?;
    let rows = grid.expand()?;
    let seeds: Vec<Option<u64>> = if spec.seeds.is_empty() {
        vec![None]
    } else {
        spec.seeds.iter().copied().map(Some).collect()
    };
    let mut jobs = Vec::new();
    let mut index = 0usize;
    for row in rows {
        for seed in &seeds {
            let job_id = format!("{index:04}");
            jobs.push(ExperimentJob {
                schema_version: SCHEMA_VERSION,
                job_id,
                experiment: spec.name.clone(),
                params: row.clone(),
                seed: *seed,
            });
            index += 1;
        }
    }
    Ok(ExperimentPlan {
        schema_version: SCHEMA_VERSION,
        experiment: spec.name.clone(),
        jobs,
    })
}
