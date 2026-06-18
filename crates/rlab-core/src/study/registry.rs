use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::config::apply_dotted_overrides;
use crate::error::{RlabError, RlabResult};
use crate::experiments::{matrix::Grid, ExperimentJob};
use crate::registry::{Registry, RegistryKind, RegistryRecord};

const SCHEMA_VERSION: u32 = 1;
const DEFAULT_QUALIFICATION_SEED: u64 = 42;
const KEY_AXES: &str = "axes";
const KEY_CONDITIONS: &str = "conditions";
const KEY_EXPERIMENTS: &str = "experiments";
const KEY_EXPERIMENT_SELECTOR: &str = "experiment_selector";
const KEY_KIND: &str = "kind";
const KEY_MATRIX: &str = "matrix";
const KEY_METADATA: &str = "metadata";
const KEY_PARAMS: &str = "params";
const KEY_QUALIFICATION: &str = "qualification";
const KEY_SEED: &str = "seed";
const KEY_SEEDS: &str = "seeds";
const KEY_TAGS: &str = "tags";
const KEY_VARIANTS: &str = "variants";

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
    default_params: &BTreeMap<String, Value>,
    explicit_params: &BTreeMap<String, Value>,
) -> RlabResult<RegistryStudyPlan> {
    let study = registry
        .find(RegistryKind::STUDY, study_name)
        .ok_or_else(|| RlabError::validation(format!("unknown study: {study_name}")))?;
    let qualification = parse_qualification(study)?;
    let design = parse_study_design(study)?;
    let experiment_lookup = experiment_lookup(registry);
    let experiment_cases = study_experiment_cases(registry, study, &design)?;
    if experiment_cases.is_empty() {
        return Err(RlabError::validation(format!(
            "study {study_name} does not declare experiments or conditions"
        )));
    }
    let mut jobs = Vec::new();
    for case in experiment_cases {
        let record = experiment_lookup
            .get(case.experiment.as_str())
            .ok_or_else(|| {
                RlabError::validation(format!(
                    "study {study_name} references unknown experiment {}",
                    case.experiment
                ))
            })?;
        let experiment = parse_experiment_design(record)?;
        reject_qualification_collisions(
            record,
            &experiment.matrix,
            &design.axes,
            &design.variants,
            &qualification.params,
        )?;
        append_study_jobs(
            &mut jobs,
            &experiment,
            &design,
            &case,
            mode,
            &qualification,
            default_params,
            explicit_params,
        )?;
    }

    Ok(RegistryStudyPlan {
        schema_version: SCHEMA_VERSION,
        study: study_name.to_owned(),
        mode,
        jobs,
    })
}

struct ExperimentDesign {
    name: String,
    params: BTreeMap<String, Value>,
    matrix: BTreeMap<String, Vec<Value>>,
    seeds: Vec<u64>,
}

struct StudyDesign {
    params: BTreeMap<String, Value>,
    axes: BTreeMap<String, Vec<Value>>,
    variants: BTreeMap<String, BTreeMap<String, Value>>,
    conditions: Vec<ConditionDesign>,
    seeds: Vec<u64>,
}

struct ConditionDesign {
    name: String,
    experiment: String,
    params: BTreeMap<String, Value>,
}

struct ExperimentCase {
    condition: Option<String>,
    experiment: String,
    params: BTreeMap<String, Value>,
}

fn experiment_lookup(registry: &Registry) -> BTreeMap<String, &RegistryRecord> {
    registry
        .records_by_kind_ref(&RegistryKind::EXPERIMENT)
        .into_iter()
        .map(|record| (record.name.clone(), record))
        .collect()
}

fn study_experiment_cases(
    registry: &Registry,
    study: &RegistryRecord,
    design: &StudyDesign,
) -> RlabResult<Vec<ExperimentCase>> {
    if !design.conditions.is_empty() {
        if !string_array(study, KEY_EXPERIMENTS)?.is_empty()
            || study.metadata.contains_key(KEY_EXPERIMENT_SELECTOR)
        {
            return Err(RlabError::validation(
                "study conditions cannot be mixed with experiments or experiment_selector",
            ));
        }
        return Ok(design
            .conditions
            .iter()
            .map(|condition| ExperimentCase {
                condition: Some(condition.name.clone()),
                experiment: condition.experiment.clone(),
                params: condition.params.clone(),
            })
            .collect());
    }

    Ok(study_experiments(registry, study)?
        .into_iter()
        .map(|experiment| ExperimentCase {
            condition: None,
            experiment,
            params: BTreeMap::new(),
        })
        .collect())
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

fn metadata_value(record: &RegistryRecord, key: &str, default: Value) -> Value {
    match record.metadata.get(key) {
        Some(value) => value.clone(),
        None => default,
    }
}

struct Qualification {
    params: BTreeMap<String, Value>,
    seed: u64,
}

fn parse_experiment_design(record: &RegistryRecord) -> RlabResult<ExperimentDesign> {
    let name = record.name.clone();
    Ok(ExperimentDesign {
        name,
        params: decode_record_metadata(record, KEY_PARAMS, Value::Object(Default::default()))?,
        matrix: decode_record_metadata(record, KEY_MATRIX, Value::Object(Default::default()))?,
        seeds: decode_record_metadata(record, KEY_SEEDS, Value::Array(Vec::new()))?,
    })
}

fn parse_study_design(record: &RegistryRecord) -> RlabResult<StudyDesign> {
    let axes: BTreeMap<String, Vec<Value>> =
        decode_record_metadata(record, KEY_AXES, Value::Object(Default::default()))?;
    Grid::validate_axes(&axes)?;

    Ok(StudyDesign {
        params: decode_record_metadata(record, KEY_PARAMS, Value::Object(Default::default()))?,
        axes,
        variants: parse_variants(record)?,
        conditions: parse_conditions(record)?,
        seeds: decode_record_metadata(record, KEY_SEEDS, Value::Array(Vec::new()))?,
    })
}

fn parse_conditions(record: &RegistryRecord) -> RlabResult<Vec<ConditionDesign>> {
    let value = metadata_value(record, KEY_CONDITIONS, Value::Array(Vec::new()));
    let array = value
        .as_array()
        .ok_or_else(|| RlabError::validation("study conditions must be an array"))?;
    let mut names = std::collections::BTreeSet::new();
    let mut conditions = Vec::with_capacity(array.len());
    for value in array {
        let object = value
            .as_object()
            .ok_or_else(|| RlabError::validation("study condition must be an object"))?;
        let name = object
            .get("name")
            .and_then(Value::as_str)
            .ok_or_else(|| RlabError::validation("study condition name must be a string"))?;
        if name.trim().is_empty() {
            return Err(RlabError::validation(
                "study condition name cannot be empty",
            ));
        }
        if !names.insert(name.to_owned()) {
            return Err(RlabError::validation(format!(
                "duplicate study condition name: {name}"
            )));
        }
        let experiment = object
            .get("experiment")
            .and_then(Value::as_str)
            .ok_or_else(|| RlabError::validation("study condition experiment must be a string"))?;
        if experiment.trim().is_empty() {
            return Err(RlabError::validation(
                "study condition experiment cannot be empty",
            ));
        }
        let params = match object.get(KEY_PARAMS) {
            Some(value) => serde_json::from_value(value.clone()).map_err(|error| {
                RlabError::validation(format!("invalid study condition {name} params: {error}"))
            })?,
            None => BTreeMap::new(),
        };
        conditions.push(ConditionDesign {
            name: name.to_owned(),
            experiment: experiment.to_owned(),
            params,
        });
    }
    Ok(conditions)
}

fn parse_variants(
    record: &RegistryRecord,
) -> RlabResult<BTreeMap<String, BTreeMap<String, Value>>> {
    let value = metadata_value(record, KEY_VARIANTS, Value::Object(Default::default()));
    let object = value
        .as_object()
        .ok_or_else(|| RlabError::validation("study variants must be an object"))?;
    let mut variants = BTreeMap::new();
    for (name, value) in object {
        if name.trim().is_empty() {
            return Err(RlabError::validation("study variant name cannot be empty"));
        }
        let overrides = value.as_object().ok_or_else(|| {
            RlabError::validation(format!("study variant {name} must be an object"))
        })?;
        variants.insert(
            name.clone(),
            overrides
                .iter()
                .map(|(key, value)| (key.clone(), value.clone()))
                .collect(),
        );
    }
    Ok(variants)
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

fn decode_record_metadata<T: serde::de::DeserializeOwned>(
    record: &RegistryRecord,
    key: &str,
    default: Value,
) -> RlabResult<T> {
    serde_json::from_value(metadata_value(record, key, default)).map_err(|error| {
        RlabError::validation(format!("invalid {} {key}: {error}", record.kind.as_str()))
    })
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

fn reject_qualification_collisions(
    record: &RegistryRecord,
    experiment_matrix: &BTreeMap<String, Vec<Value>>,
    study_axes: &BTreeMap<String, Vec<Value>>,
    variants: &BTreeMap<String, BTreeMap<String, Value>>,
    qualification: &BTreeMap<String, Value>,
) -> RlabResult<()> {
    let variant_keys = variants
        .values()
        .flat_map(|overrides| overrides.keys())
        .collect::<std::collections::BTreeSet<_>>();
    let collisions: Vec<&str> = qualification
        .keys()
        .filter(|key| {
            experiment_matrix.contains_key(*key)
                || study_axes.contains_key(*key)
                || variant_keys.contains(*key)
        })
        .map(String::as_str)
        .collect();
    if collisions.is_empty() {
        return Ok(());
    }
    Err(RlabError::validation(format!(
        "qualification params overlap planned axes for {}: {}",
        record.name,
        collisions.join(", ")
    )))
}

fn append_study_jobs(
    output: &mut Vec<ExperimentJob>,
    experiment: &ExperimentDesign,
    study: &StudyDesign,
    case: &ExperimentCase,
    mode: StudyMode,
    qualification: &Qualification,
    default_params: &BTreeMap<String, Value>,
    explicit_params: &BTreeMap<String, Value>,
) -> RlabResult<()> {
    let experiment_rows = Grid::expand_axes(&experiment.matrix)?;
    let study_rows = Grid::expand_axes(&study.axes)?;
    let variant_rows = variant_rows(&study.variants);
    let full_seeds = effective_full_seeds(&study.seeds, &experiment.seeds);
    let planned_jobs = planned_job_count(
        experiment_rows.len(),
        study_rows.len(),
        variant_rows.len(),
        full_seeds.len(),
        mode,
    )?;
    output.reserve(planned_jobs);
    let mut cell_index = 0usize;
    let base_params = base_params_value(
        default_params,
        &experiment.params,
        &study.params,
        &case.params,
    )?;

    for experiment_row in &experiment_rows {
        for study_row in &study_rows {
            for (variant_name, variant_overrides) in &variant_rows {
                let mut params = base_params.clone();
                apply_dotted_overrides(&mut params, experiment_row, false)?;
                apply_dotted_overrides(&mut params, study_row, false)?;
                apply_declared_overrides_value(&mut params, variant_overrides)?;
                if mode == StudyMode::Qualification {
                    apply_runtime_overrides_value(&mut params, &qualification.params);
                    apply_runtime_overrides_value(&mut params, explicit_params);
                    push_study_job(
                        output,
                        experiment,
                        case.condition.clone(),
                        variant_name.clone(),
                        cell_index,
                        value_to_params(params)?,
                        Some(qualification.seed),
                    );
                } else {
                    for seed in &full_seeds {
                        let mut seeded = params.clone();
                        apply_runtime_overrides_value(&mut seeded, explicit_params);
                        push_study_job(
                            output,
                            experiment,
                            case.condition.clone(),
                            variant_name.clone(),
                            cell_index,
                            value_to_params(seeded)?,
                            *seed,
                        );
                    }
                }
                cell_index += 1;
            }
        }
    }

    Ok(())
}

fn planned_job_count(
    experiment_rows: usize,
    study_rows: usize,
    variants: usize,
    full_seeds: usize,
    mode: StudyMode,
) -> RlabResult<usize> {
    let seed_count = if mode == StudyMode::Qualification {
        1
    } else {
        full_seeds
    };
    experiment_rows
        .checked_mul(study_rows)
        .and_then(|count| count.checked_mul(variants))
        .and_then(|count| count.checked_mul(seed_count))
        .ok_or_else(|| RlabError::validation("study plan is too large"))
}

fn variant_rows(
    variants: &BTreeMap<String, BTreeMap<String, Value>>,
) -> Vec<(Option<String>, BTreeMap<String, Value>)> {
    if variants.is_empty() {
        return vec![(None, BTreeMap::new())];
    }
    variants
        .iter()
        .map(|(name, overrides)| (Some(name.clone()), overrides.clone()))
        .collect()
}

fn effective_full_seeds(study_seeds: &[u64], experiment_seeds: &[u64]) -> Vec<Option<u64>> {
    let seeds = if study_seeds.is_empty() {
        experiment_seeds
    } else {
        study_seeds
    };
    if seeds.is_empty() {
        vec![None]
    } else {
        seeds.iter().copied().map(Some).collect()
    }
}

fn base_params_value(
    default_params: &BTreeMap<String, Value>,
    experiment_params: &BTreeMap<String, Value>,
    study_params: &BTreeMap<String, Value>,
    condition_params: &BTreeMap<String, Value>,
) -> RlabResult<Value> {
    let mut value = Value::Object(serde_json::Map::new());
    extend_params_object(&mut value, default_params);
    extend_params_object(&mut value, experiment_params);
    extend_params_object(&mut value, study_params);
    apply_declared_overrides_value(&mut value, condition_params)?;
    Ok(value)
}

fn extend_params_object(params: &mut Value, overrides: &BTreeMap<String, Value>) {
    let Value::Object(object) = params else {
        return;
    };
    object.extend(
        overrides
            .iter()
            .map(|(key, value)| (key.clone(), value.clone())),
    );
}

fn apply_declared_overrides_value(
    params: &mut Value,
    overrides: &BTreeMap<String, Value>,
) -> RlabResult<()> {
    let mut flat = BTreeMap::new();
    for (key, value) in overrides {
        if key.contains('.') {
            let dotted = BTreeMap::from([(key.clone(), value.clone())]);
            apply_dotted_overrides(params, &dotted, false)?;
        } else {
            flat.insert(key.clone(), value.clone());
        }
    }
    extend_params_object(params, &flat);
    Ok(())
}

fn apply_runtime_overrides_value(params: &mut Value, overrides: &BTreeMap<String, Value>) {
    for (key, value) in overrides {
        if key.contains('.') {
            let mut patched = params.clone();
            let dotted = BTreeMap::from([(key.clone(), value.clone())]);
            if apply_dotted_overrides(&mut patched, &dotted, false).is_ok() {
                *params = patched;
                continue;
            }
        }
        if let Value::Object(object) = params {
            object.insert(key.clone(), value.clone());
        }
    }
}

fn value_to_params(value: Value) -> RlabResult<BTreeMap<String, Value>> {
    match value {
        Value::Object(object) => Ok(object.into_iter().collect()),
        other => serde_json::from_value(other).map_err(RlabError::serialization),
    }
}

fn push_study_job(
    output: &mut Vec<ExperimentJob>,
    experiment: &ExperimentDesign,
    condition: Option<String>,
    variant: Option<String>,
    cell: usize,
    params: BTreeMap<String, Value>,
    seed: Option<u64>,
) {
    output.push(ExperimentJob {
        schema_version: SCHEMA_VERSION,
        job_id: format!("{:04}", output.len()),
        experiment: experiment.name.clone(),
        condition,
        variant,
        cell: Some(cell),
        params,
        seed,
    });
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
                "matrix": {"width": [128, 256]},
                "seeds": [1, 2],
                "metrics": []
            }),
        );
        let explicit = BTreeMap::from([("runtime.max_words_seen".to_owned(), json!(50))]);

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Qualification,
            &BTreeMap::new(),
            &explicit,
        )
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
                "matrix": {"width": [128, 256]},
                "seeds": [1, 2],
                "metrics": []
            }),
        );

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
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
    fn study_params_axes_variants_and_seeds_expand_in_rust() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "params": {
                    "model": {
                        "ref": "model:toy",
                        "params": {
                            "width": 128,
                            "embedding": {"ref": "embedding:euclidean", "params": {"dim": 32}}
                        }
                    },
                    "seq_len": 128
                },
                "axes": {"seq_len": [128, 256]},
                "variants": {
                    "euclidean": {
                        "model.params.embedding": {
                            "ref": "embedding:euclidean",
                            "params": {"dim": 32}
                        }
                    },
                    "hyperbolic": {
                        "model.params.embedding": {
                            "ref": "embedding:hyperbolic",
                            "params": {"dim": 32, "curvature": 0.1}
                        }
                    }
                },
                "seeds": [3, 5]
            }),
            json!({
                "params": {"batch_size": 32},
                "matrix": {"model.params.width": [128, 256]},
                "seeds": [1],
                "metrics": []
            }),
        );

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect("valid full study plan");

        assert_eq!(plan.jobs.len(), 16);
        assert_eq!(plan.jobs[0].variant.as_deref(), Some("euclidean"));
        assert_eq!(plan.jobs[0].cell, Some(0));
        assert_eq!(plan.jobs[0].seed, Some(3));
        assert_eq!(plan.jobs[1].seed, Some(5));
        assert_eq!(plan.jobs[0].params.get("batch_size"), Some(&json!(32)));
        assert_eq!(plan.jobs[0].params.get("seq_len"), Some(&json!(128)));
        assert_eq!(plan.jobs[0].params["model"]["params"]["width"], json!(128));
        assert_eq!(
            plan.jobs[2].params["model"]["params"]["embedding"]["ref"],
            json!("embedding:hyperbolic")
        );
    }

    #[test]
    fn qualification_uses_one_seed_per_planned_cell() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "axes": {"seq_len": [128, 256]},
                "seeds": [1, 2],
                "qualification": {"seed": 9, "params": {"max_words": 100}}
            }),
            json!({
                "params": {"max_words": 1000},
                "seeds": [3, 4],
                "metrics": []
            }),
        );

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Qualification,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect("valid qualification plan");

        assert_eq!(plan.jobs.len(), 2);
        assert!(plan.jobs.iter().all(|job| job.seed == Some(9)));
        assert!(plan
            .jobs
            .iter()
            .all(|job| job.params.get("max_words") == Some(&json!(100))));
    }

    #[test]
    fn conditions_select_experiments_without_cross_product() {
        let mut registry = Registry::new();
        registry
            .insert(record(
                RegistryKind::STUDY,
                "all",
                json!({
                    "params": {
                        "model": {
                            "ref": "model:toy",
                            "params": {"heads": {"lm": {"ref": "head:lm"}}}
                        },
                        "max_words": 1000
                    },
                    "conditions": [
                        {
                            "name": "mtp",
                            "experiment": "hybrid_mtp",
                            "params": {"model.params.heads": {
                                "lm": {"ref": "head:lm"},
                                "mtp": {"ref": "head:mtp"}
                            }}
                        },
                        {
                            "name": "rtd",
                            "experiment": "hybrid_rtd",
                            "params": {"model.params.heads": {
                                "lm": {"ref": "head:lm"},
                                "rtd": {"ref": "head:rtd"}
                            }}
                        }
                    ],
                    "seeds": [1, 2]
                }),
            ))
            .expect("valid study record");
        registry
            .insert(record(
                RegistryKind::EXPERIMENT,
                "hybrid_mtp",
                json!({"params": {}, "metrics": []}),
            ))
            .expect("valid mtp experiment");
        registry
            .insert(record(
                RegistryKind::EXPERIMENT,
                "hybrid_rtd",
                json!({"params": {}, "metrics": []}),
            ))
            .expect("valid rtd experiment");

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect("valid full plan");

        assert_eq!(plan.jobs.len(), 4);
        assert_eq!(plan.jobs[0].condition.as_deref(), Some("mtp"));
        assert_eq!(plan.jobs[0].experiment, "hybrid_mtp");
        assert_eq!(
            plan.jobs[0].params["model"]["params"]["heads"]["mtp"]["ref"],
            json!("head:mtp")
        );
        assert_eq!(plan.jobs[2].condition.as_deref(), Some("rtd"));
        assert_eq!(plan.jobs[2].experiment, "hybrid_rtd");
        assert_eq!(
            plan.jobs[2].params["model"]["params"]["heads"]["rtd"]["ref"],
            json!("head:rtd")
        );
    }

    #[test]
    fn run_defaults_merge_before_study_and_cli_params() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "params": {"device": "cuda", "max_words": 1000},
                "qualification": {"params": {"max_words": 100}}
            }),
            json!({"params": {}, "metrics": []}),
        );
        let defaults = BTreeMap::from([
            ("device".to_owned(), json!("auto")),
            ("seed_note".to_owned(), json!("lab")),
        ]);
        let explicit = BTreeMap::from([("max_words".to_owned(), json!(50))]);

        let plan = plan_registry_study(
            &registry,
            "all",
            StudyMode::Qualification,
            &defaults,
            &explicit,
        )
        .expect("valid qualification plan");

        assert_eq!(plan.jobs[0].params.get("device"), Some(&json!("cuda")));
        assert_eq!(plan.jobs[0].params.get("seed_note"), Some(&json!("lab")));
        assert_eq!(plan.jobs[0].params.get("max_words"), Some(&json!(50)));
    }

    #[test]
    fn condition_names_must_be_unique() {
        let registry = registry(
            json!({
                "conditions": [
                    {"name": "same", "experiment": "scaling"},
                    {"name": "same", "experiment": "scaling"}
                ]
            }),
            json!({"params": {}, "metrics": []}),
        );

        let error = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect_err("duplicate condition names must fail");

        assert!(error.to_string().contains("duplicate study condition"));
    }

    #[test]
    fn conditions_cannot_mix_with_experiment_selector() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "conditions": [{"name": "case", "experiment": "scaling"}]
            }),
            json!({"params": {}, "metrics": []}),
        );

        let error = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect_err("mixed study modes must fail");

        assert!(error.to_string().contains("conditions cannot be mixed"));
    }

    #[test]
    fn qualification_rejects_planned_axis_overrides() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "axes": {"width": [128, 256]},
                "qualification": {"params": {"width": 64}}
            }),
            json!({
                "params": {},
                "matrix": {},
                "seeds": [1],
                "metrics": []
            }),
        );

        let error = plan_registry_study(
            &registry,
            "all",
            StudyMode::Qualification,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect_err("matrix collision must fail");

        assert!(error.to_string().contains("overlap"));
    }

    #[test]
    fn empty_study_axes_are_rejected() {
        let registry = registry(
            json!({
                "experiments": ["scaling"],
                "axes": {"seq_len": []}
            }),
            json!({"params": {}, "metrics": []}),
        );

        let error = plan_registry_study(
            &registry,
            "all",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
        .expect_err("empty axis must fail");

        assert!(error.to_string().contains("has no values"));
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

        let error = plan_registry_study(
            &registry,
            "all",
            StudyMode::Qualification,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
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

        let plan = plan_registry_study(
            &registry,
            "selected",
            StudyMode::Full,
            &BTreeMap::new(),
            &BTreeMap::new(),
        )
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
