use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
use crate::experiments::{plan_record_experiment, ExperimentJob};
use crate::registry::{Registry, RegistryKind, RegistryRecord};

const SCHEMA_VERSION: u32 = 1;
const DEFAULT_QUALIFICATION_SEED: u64 = 42;
const KEY_EXPERIMENTS: &str = "experiments";
const KEY_MATRIX: &str = "matrix";
const KEY_PARAMS: &str = "params";
const KEY_QUALIFICATION: &str = "qualification";
const KEY_SEED: &str = "seed";

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum StudyMode {
    Qualification,
    Full,
}

impl StudyMode {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Qualification => "qualification",
            Self::Full => "full",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistryStudyPlan {
    pub schema_version: u32,
    pub study: String,
    pub mode: StudyMode,
    pub jobs: Vec<ExperimentJob>,
}

pub fn plan_registry_study(
    registry: &Registry,
    study_name: &str,
    mode: StudyMode,
    explicit_params: &BTreeMap<String, Value>,
) -> RlabResult<RegistryStudyPlan> {
    let study = registry
        .find(RegistryKind::STUDY, study_name)
        .ok_or_else(|| RlabError::validation(format!("unknown study: {study_name}")))?;
    let experiments = string_array(study, KEY_EXPERIMENTS)?;
    if experiments.is_empty() {
        return Err(RlabError::validation(format!(
            "study {study_name} does not declare experiments"
        )));
    }

    let qualification = parse_qualification(study)?;
    let mut jobs = Vec::new();
    for experiment_name in experiments {
        let record = registry
            .find(RegistryKind::EXPERIMENT, &experiment_name)
            .ok_or_else(|| {
                RlabError::validation(format!(
                    "study {study_name} references unknown experiment {experiment_name}"
                ))
            })?;
        reject_matrix_collisions(record, &qualification.params)?;
        let planned = plan_record_experiment(record)?;
        let selected = match mode {
            StudyMode::Full => planned,
            StudyMode::Qualification => qualification_jobs(planned, qualification.seed),
        };
        append_jobs(
            &mut jobs,
            selected,
            mode,
            &qualification.params,
            explicit_params,
        );
    }

    Ok(RegistryStudyPlan {
        schema_version: SCHEMA_VERSION,
        study: study_name.to_owned(),
        mode,
        jobs,
    })
}

struct Qualification {
    params: BTreeMap<String, Value>,
    seed: u64,
}

fn parse_qualification(record: &RegistryRecord) -> RlabResult<Qualification> {
    let Some(value) = record.metadata.get(KEY_QUALIFICATION) else {
        return Ok(Qualification {
            params: BTreeMap::new(),
            seed: DEFAULT_QUALIFICATION_SEED,
        });
    };
    let object = value
        .as_object()
        .ok_or_else(|| RlabError::validation("study qualification must be an object"))?;
    let seed = match object.get(KEY_SEED) {
        Some(value) => value.as_u64().ok_or_else(|| {
            RlabError::validation("study qualification seed must be a non-negative integer")
        })?,
        None => DEFAULT_QUALIFICATION_SEED,
    };
    let params = match object.get(KEY_PARAMS) {
        Some(value) => serde_json::from_value(value.clone()).map_err(|error| {
            RlabError::validation(format!("invalid study qualification params: {error}"))
        })?,
        None => BTreeMap::new(),
    };
    Ok(Qualification { params, seed })
}

fn string_array(record: &RegistryRecord, key: &str) -> RlabResult<Vec<String>> {
    match record.metadata.get(key) {
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|error| RlabError::validation(format!("invalid study {key}: {error}"))),
        None => Ok(Vec::new()),
    }
}

fn reject_matrix_collisions(
    record: &RegistryRecord,
    qualification: &BTreeMap<String, Value>,
) -> RlabResult<()> {
    let Some(matrix) = record.metadata.get(KEY_MATRIX).and_then(Value::as_object) else {
        return Ok(());
    };
    let collisions: Vec<&str> = qualification
        .keys()
        .filter(|key| matrix.contains_key(*key))
        .map(String::as_str)
        .collect();
    if collisions.is_empty() {
        return Ok(());
    }
    Err(RlabError::validation(format!(
        "qualification params overlap experiment matrix axes for {}: {}",
        record.name,
        collisions.join(", ")
    )))
}

fn qualification_jobs(jobs: Vec<ExperimentJob>, seed: u64) -> Vec<ExperimentJob> {
    let mut selected: Vec<ExperimentJob> = Vec::new();
    for mut job in jobs {
        let repeated_cell = match selected.last() {
            Some(previous) => previous.params == job.params,
            None => false,
        };
        if repeated_cell {
            continue;
        }
        job.seed = Some(seed);
        selected.push(job);
    }
    selected
}

fn append_jobs(
    output: &mut Vec<ExperimentJob>,
    jobs: Vec<ExperimentJob>,
    mode: StudyMode,
    qualification_params: &BTreeMap<String, Value>,
    explicit_params: &BTreeMap<String, Value>,
) {
    output.reserve(jobs.len());
    for mut job in jobs {
        if mode == StudyMode::Qualification {
            job.params.extend(qualification_params.clone());
        }
        job.params.extend(explicit_params.clone());
        job.job_id = format!("{:04}", output.len());
        output.push(job);
    }
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use serde_json::json;

    use super::*;

    #[test]
    fn qualification_covers_each_cell_once_with_explicit_precedence() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "qualification": {
                    "seed": 7,
                    "params": {"runtime.max_words_seen": 200}
                }
            }),
            json!({
                "params": {"config": "scaling"},
                "matrix": {"model.width": [128, 256]},
                "seeds": [1, 2],
                "metrics": []
            }),
        );
        let explicit = BTreeMap::from([("runtime.max_words_seen".to_owned(), json!(50))]);

        let plan = plan_registry_study(&registry, "all", StudyMode::Qualification, &explicit)
            .expect("valid qualification plan");

        assert_eq!(plan.jobs.len(), 2);
        assert!(plan.jobs.iter().all(|job| job.seed == Some(7)));
        assert!(plan
            .jobs
            .iter()
            .all(|job| job.params.get("runtime.max_words_seen") == Some(&json!(50))));
    }

    #[test]
    fn full_plan_retains_every_seed() {
        let registry = registry(
            json!({"experiments": ["scaling"]}),
            json!({
                "params": {},
                "matrix": {"model.width": [128, 256]},
                "seeds": [1, 2],
                "metrics": []
            }),
        );

        let plan = plan_registry_study(&registry, "all", StudyMode::Full, &BTreeMap::new())
            .expect("valid full plan");

        assert_eq!(plan.jobs.len(), 4);
        assert_eq!(
            plan.jobs
                .iter()
                .filter_map(|job| job.seed)
                .collect::<Vec<_>>(),
            vec![1, 2, 1, 2]
        );
    }

    #[test]
    fn qualification_rejects_matrix_axis_overrides() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "qualification": {"params": {"model.width": 64}}
            }),
            json!({
                "params": {},
                "matrix": {"model.width": [128, 256]},
                "seeds": [1],
                "metrics": []
            }),
        );

        let error =
            plan_registry_study(&registry, "all", StudyMode::Qualification, &BTreeMap::new())
                .expect_err("matrix collision must fail");

        assert!(error.to_string().contains("overlap"));
    }

    #[test]
    fn study_rejects_unknown_experiment() {
        let mut registry = Registry::new();
        registry
            .insert(record(
                RegistryKind::STUDY,
                "all",
                json!({"experiments": ["missing"]}),
            ))
            .expect("valid study record");

        let error =
            plan_registry_study(&registry, "all", StudyMode::Qualification, &BTreeMap::new())
                .expect_err("unknown experiment must fail");

        assert!(error.to_string().contains("unknown experiment"));
    }

    fn registry(study: Value, experiment: Value) -> Registry {
        let mut registry = Registry::new();
        registry
            .insert(record(RegistryKind::STUDY, "all", study))
            .expect("valid study record");
        registry
            .insert(record(RegistryKind::EXPERIMENT, "scaling", experiment))
            .expect("valid experiment record");
        registry
    }

    fn record(kind: RegistryKind, name: &str, metadata: Value) -> RegistryRecord {
        RegistryRecord {
            schema_version: 1,
            kind,
            name: name.to_owned(),
            version: "1".to_owned(),
            module: "tests".to_owned(),
            qualname: name.to_owned(),
            source: PathBuf::from("tests.py"),
            tags: Vec::new(),
            description: String::new(),
            metadata: serde_json::from_value(metadata).expect("object metadata"),
        }
    }
}
