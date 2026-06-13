use std::collections::BTreeMap;

use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::matrix::Grid;
use super::model::{ExperimentJob, ExperimentPlan, ExperimentSpec};

const SCHEMA_VERSION: u32 = 1;

pub fn plan_experiment(spec: &ExperimentSpec) -> RlabResult<ExperimentPlan> {
    spec.validate()?;

    let rows = Grid::expand_axes(&spec.matrix)?;
    let mut jobs = Vec::with_capacity(job_count(rows.len(), spec.seeds.len())?);
    let mut index = 0usize;

    if spec.seeds.is_empty() {
        for row in &rows {
            push_experiment_job(&mut jobs, spec, row, None, &mut index);
        }
    } else {
        for row in &rows {
            for seed in &spec.seeds {
                push_experiment_job(&mut jobs, spec, row, Some(*seed), &mut index);
            }
        }
    }

    Ok(ExperimentPlan {
        schema_version: SCHEMA_VERSION,
        experiment: spec.name.clone(),
        jobs,
    })
}

fn push_experiment_job(
    jobs: &mut Vec<ExperimentJob>,
    spec: &ExperimentSpec,
    row: &BTreeMap<String, Value>,
    seed: Option<u64>,
    index: &mut usize,
) {
    jobs.push(experiment_job(spec, row, seed, *index));
    *index += 1;
}

fn experiment_job(
    spec: &ExperimentSpec,
    row: &BTreeMap<String, Value>,
    seed: Option<u64>,
    index: usize,
) -> ExperimentJob {
    ExperimentJob {
        schema_version: SCHEMA_VERSION,
        job_id: format!("{index:04}"),
        experiment: spec.name.clone(),
        params: merged_params(&spec.params, row),
        seed,
    }
}

fn merged_params(
    base: &BTreeMap<String, Value>,
    row: &BTreeMap<String, Value>,
) -> BTreeMap<String, Value> {
    let mut params = base.clone();

    for (key, value) in row {
        params.insert(key.clone(), value.clone());
    }

    params
}

fn job_count(row_count: usize, seed_count: usize) -> RlabResult<usize> {
    let effective_seed_count = if seed_count == 0 { 1 } else { seed_count };

    match row_count.checked_mul(effective_seed_count) {
        Some(count) => Ok(count),
        None => Err(RlabError::validation("experiment plan is too large")),
    }
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
            params: BTreeMap::new(),
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

        let plan = valid_plan(&spec);

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
            params: BTreeMap::new(),
            matrix: BTreeMap::new(),
            metrics: Vec::new(),
            seeds: vec![1, 2, 3],
            retry: RetryPolicy::none(),
        };

        let plan = valid_plan(&spec);

        assert_eq!(plan.jobs.len(), 3);
        assert!(plan.jobs.iter().all(|job| job.params.is_empty()));
    }

    #[test]
    fn fixed_params_are_combined_with_matrix() {
        let spec = ExperimentSpec {
            schema_version: 1,
            name: "configured".to_string(),
            question: None,
            hypothesis: None,
            params: BTreeMap::from([("config".to_string(), json!("base"))]),
            matrix: BTreeMap::from([("model.width".to_string(), vec![json!(32)])]),
            metrics: Vec::new(),
            seeds: vec![7],
            retry: RetryPolicy::none(),
        };

        let plan = valid_plan(&spec);
        let Some(job) = plan.jobs.first() else {
            panic!("expected at least one planned job");
        };

        assert_eq!(job.params.get("config"), Some(&json!("base")));
        assert_eq!(job.params.get("model.width"), Some(&json!(32)));
    }

    fn valid_plan(spec: &ExperimentSpec) -> ExperimentPlan {
        match plan_experiment(spec) {
            Ok(plan) => plan,
            Err(error) => panic!("expected valid experiment plan: {error}"),
        }
    }
}
