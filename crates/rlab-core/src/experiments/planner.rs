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

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use serde_json::json;

    use super::*;
    use crate::experiments::RetryPolicy;

    #[test]
    fn expands_matrix_times_seeds() {
        let spec = ExperimentSpec {
            schema_version: 1,
            name: "embedding".to_string(),
            question: None,
            hypothesis: None,
            matrix: BTreeMap::from([
                (
                    "embedding".to_string(),
                    vec![json!("euclidean"), json!("hyperbolic")],
                ),
                ("batch_size".to_string(), vec![json!(16), json!(32)]),
            ]),
            metrics: vec!["validation.loss".to_string()],
            seeds: vec![7, 11],
            retry: RetryPolicy::none(),
        };

        let plan = plan_experiment(&spec).expect("valid experiment plan");

        assert_eq!(plan.jobs.len(), 8);
        assert_eq!(
            plan.jobs
                .iter()
                .filter_map(|job| job.seed)
                .collect::<Vec<_>>(),
            vec![7, 11, 7, 11, 7, 11, 7, 11]
        );
        assert!(plan.jobs.iter().all(|job| job.params.len() == 2));
    }

    #[test]
    fn seed_only_experiment_produces_one_job_per_seed() {
        let spec = ExperimentSpec {
            schema_version: 1,
            name: "repeated".to_string(),
            question: None,
            hypothesis: None,
            matrix: BTreeMap::new(),
            metrics: Vec::new(),
            seeds: vec![1, 2, 3],
            retry: RetryPolicy::none(),
        };

        let plan = plan_experiment(&spec).expect("valid experiment plan");

        assert_eq!(plan.jobs.len(), 3);
        assert!(plan.jobs.iter().all(|job| job.params.is_empty()));
    }
}
