use std::borrow::Cow;
use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::schema::REGISTRY_SCHEMA_VERSION;
use super::validate::validate_registry_record;

const INVALID_REGISTRY_KIND_PREFIX: &str = "invalid registry kind";
const DUPLICATE_REGISTRY_RECORD_PREFIX: &str = "duplicate registry record";

const KIND_EXPERIMENT: &str = "experiment";
const KIND_BENCHMARK: &str = "benchmark";
const KIND_WORKFLOW: &str = "workflow";
const KIND_EVALUATION: &str = "evaluation";
const KIND_EXTERNAL_EVALUATION: &str = "external_evaluation";
const KIND_RESULT_SCHEMA: &str = "result_schema";
const KIND_STUDY: &str = "study";
const KIND_SOURCE: &str = "source";
const KIND_TRANSFORM: &str = "transform";
const KIND_FILTER: &str = "filter";
const KIND_GROUP: &str = "group";
const KIND_DEDUP: &str = "dedup";
const KIND_SINK: &str = "sink";
const KIND_CHECK: &str = "check";
const KIND_METRIC: &str = "metric";
const KIND_PIPELINE: &str = "pipeline";
const KIND_DATASET: &str = "dataset";
const KIND_ADAPTER: &str = "adapter";
const KIND_LOADER: &str = "loader";

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(transparent)]
pub struct RegistryKind(Cow<'static, str>);

impl RegistryKind {
    pub const EXPERIMENT: Self = Self::constant(KIND_EXPERIMENT);
    pub const BENCHMARK: Self = Self::constant(KIND_BENCHMARK);
    pub const WORKFLOW: Self = Self::constant(KIND_WORKFLOW);
    pub const EVALUATION: Self = Self::constant(KIND_EVALUATION);
    pub const EXTERNAL_EVALUATION: Self = Self::constant(KIND_EXTERNAL_EVALUATION);
    pub const RESULT_SCHEMA: Self = Self::constant(KIND_RESULT_SCHEMA);
    pub const STUDY: Self = Self::constant(KIND_STUDY);
    pub const SOURCE: Self = Self::constant(KIND_SOURCE);
    pub const TRANSFORM: Self = Self::constant(KIND_TRANSFORM);
    pub const FILTER: Self = Self::constant(KIND_FILTER);
    pub const GROUP: Self = Self::constant(KIND_GROUP);
    pub const DEDUP: Self = Self::constant(KIND_DEDUP);
    pub const SINK: Self = Self::constant(KIND_SINK);
    pub const CHECK: Self = Self::constant(KIND_CHECK);
    pub const METRIC: Self = Self::constant(KIND_METRIC);
    pub const PIPELINE: Self = Self::constant(KIND_PIPELINE);
    pub const DATASET: Self = Self::constant(KIND_DATASET);
    pub const ADAPTER: Self = Self::constant(KIND_ADAPTER);
    pub const LOADER: Self = Self::constant(KIND_LOADER);

    const fn constant(value: &'static str) -> Self {
        Self(Cow::Borrowed(value))
    }

    pub fn parse(value: &str) -> RlabResult<Self> {
        validate_kind(value)?;

        Ok(match value {
            KIND_EXPERIMENT => Self::EXPERIMENT,
            KIND_BENCHMARK => Self::BENCHMARK,
            KIND_WORKFLOW => Self::WORKFLOW,
            KIND_EVALUATION => Self::EVALUATION,
            KIND_EXTERNAL_EVALUATION => Self::EXTERNAL_EVALUATION,
            KIND_RESULT_SCHEMA => Self::RESULT_SCHEMA,
            KIND_STUDY => Self::STUDY,
            KIND_SOURCE => Self::SOURCE,
            KIND_TRANSFORM => Self::TRANSFORM,
            KIND_FILTER => Self::FILTER,
            KIND_GROUP => Self::GROUP,
            KIND_DEDUP => Self::DEDUP,
            KIND_SINK => Self::SINK,
            KIND_CHECK => Self::CHECK,
            KIND_METRIC => Self::METRIC,
            KIND_PIPELINE => Self::PIPELINE,
            KIND_DATASET => Self::DATASET,
            KIND_ADAPTER => Self::ADAPTER,
            KIND_LOADER => Self::LOADER,
            _ => Self(Cow::Owned(value.to_string())),
        })
    }

    pub fn validate(&self) -> RlabResult<()> {
        validate_kind(self.as_str())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn validate_kind(value: &str) -> RlabResult<()> {
    if value.is_empty() || !value.chars().all(is_valid_kind_character) {
        return Err(RlabError::registry(format!("{INVALID_REGISTRY_KIND_PREFIX}: {value}")));
    }

    Ok(())
}

fn is_valid_kind_character(character: char) -> bool {
    character.is_ascii_alphanumeric() || character == '_'
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RegistryRecord {
    pub schema_version: u32,
    pub kind: RegistryKind,
    pub name: String,
    pub version: String,
    pub module: String,
    pub qualname: String,
    pub source: PathBuf,
    pub tags: Vec<String>,
    pub description: String,
    pub metadata: BTreeMap<String, Value>,
}

impl RegistryRecord {
    pub fn from_spec(spec: RegistryRecordSpec) -> Self {
        Self {
            schema_version: REGISTRY_SCHEMA_VERSION,
            kind: spec.kind,
            name: spec.name,
            version: spec.version,
            module: spec.module,
            qualname: spec.qualname,
            source: spec.source,
            tags: spec.tags,
            description: spec.description,
            metadata: spec.metadata,
        }
    }

    fn has_identity(&self, kind: &RegistryKind, name: &str) -> bool {
        self.kind == *kind && self.name == name
    }
}

pub struct RegistryRecordSpec {
    pub kind: RegistryKind,
    pub name: String,
    pub version: String,
    pub module: String,
    pub qualname: String,
    pub source: PathBuf,
    pub tags: Vec<String>,
    pub description: String,
    pub metadata: BTreeMap<String, Value>,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct Registry {
    pub schema_version: u32,
    pub records: Vec<RegistryRecord>,
}

impl Registry {
    pub fn new() -> Self {
        Self {
            schema_version: REGISTRY_SCHEMA_VERSION,
            records: Vec::new(),
        }
    }

    pub fn insert(&mut self, record: RegistryRecord) -> RlabResult<()> {
        validate_registry_record(&record)?;

        match self.find_existing(&record) {
            Some(existing) if existing == &record => Ok(()),
            Some(_) => Err(RlabError::registry(format!(
                "{DUPLICATE_REGISTRY_RECORD_PREFIX}: {}:{}",
                record.kind.as_str(),
                record.name
            ))),
            None => {
                self.records.push(record);
                Ok(())
            }
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        if self.schema_version != REGISTRY_SCHEMA_VERSION {
            return Err(RlabError::registry("unsupported registry schema version"));
        }

        for record in &self.records {
            validate_registry_record(record)?;
        }

        Ok(())
    }

    pub fn find(&self, kind: RegistryKind, name: &str) -> Option<&RegistryRecord> {
        self.find_ref(&kind, name)
    }

    pub fn find_ref(&self, kind: &RegistryKind, name: &str) -> Option<&RegistryRecord> {
        self.records
            .iter()
            .find(|record| record.has_identity(kind, name))
    }

    pub fn records_by_kind(&self, kind: RegistryKind) -> Vec<&RegistryRecord> {
        self.records_by_kind_ref(&kind)
    }

    pub fn records_by_kind_ref(&self, kind: &RegistryKind) -> Vec<&RegistryRecord> {
        self.records
            .iter()
            .filter(|record| record.kind == *kind)
            .collect()
    }

    fn find_existing(&self, record: &RegistryRecord) -> Option<&RegistryRecord> {
        self.find_ref(&record.kind, &record.name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const TEST_VERSION: &str = "0.1.0";
    const TEST_MODULE: &str = "mymodule";
    const CONFLICTING_VERSION: &str = "1.0.0";
    const PYTHON_EXTENSION: &str = "py";

    fn make_record(kind: RegistryKind, name: &str) -> RegistryRecord {
        RegistryRecord::from_spec(RegistryRecordSpec {
            kind,
            name: name.to_owned(),
            version: TEST_VERSION.to_owned(),
            module: TEST_MODULE.to_owned(),
            qualname: name.to_owned(),
            source: source_path(name),
            tags: Vec::new(),
            description: String::new(),
            metadata: BTreeMap::new(),
        })
    }

    fn source_path(name: &str) -> PathBuf {
        PathBuf::from(format!("{name}.{PYTHON_EXTENSION}"))
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }

    #[test]
    fn insert_and_find() {
        let mut registry = Registry::new();
        let record = make_record(RegistryKind::EXPERIMENT, "exp1");

        expect_ok(registry.insert(record));

        assert!(registry.find(RegistryKind::EXPERIMENT, "exp1").is_some());
        assert!(registry
            .find_ref(&RegistryKind::EXPERIMENT, "exp1")
            .is_some());
        assert!(registry.find(RegistryKind::EXPERIMENT, "other").is_none());
    }

    #[test]
    fn insert_duplicate_identical_is_idempotent() {
        let mut registry = Registry::new();
        let record = make_record(RegistryKind::BENCHMARK, "bench1");

        expect_ok(registry.insert(record.clone()));

        assert!(registry.insert(record).is_ok());
        assert_eq!(registry.records.len(), 1);
    }

    #[test]
    fn insert_duplicate_different_fails() {
        let mut registry = Registry::new();

        expect_ok(registry.insert(make_record(RegistryKind::EXPERIMENT, "exp1")));

        let mut conflicting = make_record(RegistryKind::EXPERIMENT, "exp1");
        conflicting.version = CONFLICTING_VERSION.to_owned();

        assert!(registry.insert(conflicting).is_err());
    }

    #[test]
    fn registry_kind_parse_valid() {
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_EXPERIMENT)),
            RegistryKind::EXPERIMENT
        );
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_BENCHMARK)),
            RegistryKind::BENCHMARK
        );
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_DATASET)),
            RegistryKind::DATASET
        );
    }

    #[test]
    fn registry_kind_parse_invalid() {
        assert!(RegistryKind::parse("").is_err());
        assert!(RegistryKind::parse("not-valid").is_err());
        assert_eq!(
            expect_ok(RegistryKind::parse("attention")).as_str(),
            "attention"
        );
    }

    #[test]
    fn registry_kind_as_str_roundtrip() {
        for kind in [
            RegistryKind::EXPERIMENT,
            RegistryKind::BENCHMARK,
            RegistryKind::STUDY,
            RegistryKind::DATASET,
        ] {
            assert_eq!(expect_ok(RegistryKind::parse(kind.as_str())), kind);
        }
    }

    #[test]
    fn records_by_kind_returns_matching_records() {
        let mut registry = Registry::new();

        expect_ok(registry.insert(make_record(RegistryKind::EXPERIMENT, "exp1")));
        expect_ok(registry.insert(make_record(RegistryKind::EXPERIMENT, "exp2")));
        expect_ok(registry.insert(make_record(RegistryKind::BENCHMARK, "bench1")));

        let experiments = registry.records_by_kind_ref(&RegistryKind::EXPERIMENT);

        assert_eq!(experiments.len(), 2);
        assert!(experiments
            .iter()
            .all(|record| record.kind == RegistryKind::EXPERIMENT));
    }
}
