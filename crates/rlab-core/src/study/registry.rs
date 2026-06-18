use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};
use crate::experiments::{plan_record_experiment, ExperimentJob};
use crate::registry::{Registry, RegistryKind, RegistryRecord};

const SCHEMA_VERSION: u32 = 1;
const DEFAULT_QUALIFICATION_SEED: u64 = 42;
const KEY_EXPERIMENTS: &str = "experiments";
const KEY_EXPERIMENT_SELECTOR: &str = "experiment_selector";
const KEY_KIND: &str = "kind";
const KEY_MATRIX: &str = "matrix";
const KEY_METADATA: &str = "metadata";
const KEY_PARAMS: &str = "params";
const KEY_QUALIFICATION: &str = "qualification";
const KEY_SEED: &str = "seed";
const KEY_TAGS: &str = "tags";

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
    let experiments = study_experiments(registry, study)?;
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

fn study_experiments(registry: &Registry, study: &RegistryRecord) -> RlabResult<Vec<String>> {
    let mut experiments = string_array(study, KEY_EXPERIMENTS)?;
    experiments.extend(selector_experiments(registry, study)?);
    let mut seen = std::collections::BTreeSet::new();
    experiments.retain(|name| seen.insert(name.clone()));
    Ok(experiments)
}

fn selector_experiments(registry: &Registry, study: &RegistryRecord) -> RlabResult<Vec<String>> {
    let Some(value) = study.metadata.get(KEY_EXPERIMENT_SELECTOR) else {
        return Ok(Vec::new());
    };
    let object = value
        .as_object()
        .ok_or_else(|| RlabError::validation("study experiment_selector must be an object"))?;
    let kind = match object.get(KEY_KIND) {
        Some(value) => value.as_str().ok_or_else(|| {
            RlabError::validation("study experiment_selector kind must be a string")
        })?,
        None => "experiment",
    };
    let kind = RegistryKind::parse(kind)?;
    let tags = string_array_value(object.get(KEY_TAGS), "study experiment_selector tags")?;
    let metadata = match object.get(KEY_METADATA) {
        Some(value) => value.as_object().ok_or_else(|| {
            RlabError::validation("study experiment_selector metadata must be an object")
        })?,
        None => return Ok(records_matching(registry, &kind, &tags, None)),
    };
    Ok(records_matching(registry, &kind, &tags, Some(metadata)))
}

fn records_matching(
    registry: &Registry,
    kind: &RegistryKind,
    tags: &[String],
    metadata: Option<&serde_json::Map<String, Value>>,
) -> Vec<String> {
    registry
        .records_by_kind_ref(kind)
        .into_iter()
        .filter(|record| tags.iter().all(|tag| record.tags.contains(tag)))
        .filter(|record| {
            metadata.map_or(true, |expected| {
                expected
                    .iter()
                    .all(|(key, value)| record.metadata.get(key) == Some(value))
            })
        })
        .map(|record| record.name.clone())
        .collect()
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
    string_array_value(record.metadata.get(key), &format!("study {key}"))
}

fn string_array_value(value: Option<&Value>, label: &str) -> RlabResult<Vec<String>> {
    match value {
        Some(value) => serde_json::from_value(value.clone())
            .map_err(|error| RlabError::validation(format!("invalid {label}: {error}"))),
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

    #[test]
    fn study_selector_expands_tagged_experiments() {
        let mut registry = Registry::new();
        registry
            .insert(record(
                RegistryKind::STUDY,
                "selected",
                json!({"experiment_selector": {"tags": ["smoke"]}}),
            ))
            .expect("valid study record");
        registry
            .insert(record_with_tags(
                RegistryKind::EXPERIMENT,
                "first",
                json!({"params": {}, "metrics": [], "seeds": [1]}),
                vec!["smoke".to_owned()],
            ))
            .expect("valid first experiment");
        registry
            .insert(record_with_tags(
                RegistryKind::EXPERIMENT,
                "second",
                json!({"params": {}, "metrics": [], "seeds": [1]}),
                vec!["other".to_owned()],
            ))
            .expect("valid second experiment");

        let plan = plan_registry_study(&registry, "selected", StudyMode::Full, &BTreeMap::new())
            .expect("selector study should plan");

        assert_eq!(plan.jobs.len(), 1);
        assert_eq!(plan.jobs[0].experiment, "first");
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
        record_with_tags(kind, name, metadata, Vec::new())
    }

    fn record_with_tags(
        kind: RegistryKind,
        name: &str,
        metadata: Value,
        tags: Vec<String>,
    ) -> RegistryRecord {
        RegistryRecord {
            schema_version: 1,
            kind,
            name: name.to_owned(),
            version: "1".to_owned(),
            module: "tests".to_owned(),
            qualname: name.to_owned(),
            source: PathBuf::from("tests.py"),
            tags,
            description: String::new(),
            metadata: serde_json::from_value(metadata).expect("object metadata"),
        }
    }
}
