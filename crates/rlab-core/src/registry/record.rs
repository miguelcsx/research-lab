use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::schema::REGISTRY_SCHEMA_VERSION;
use super::validate::validate_registry_record;

const UNKNOWN_REGISTRY_KIND_PREFIX: &str = "unknown registry kind";
const DUPLICATE_REGISTRY_RECORD_PREFIX: &str = "duplicate registry record";

const KIND_EXPERIMENT: &str = "experiment";
const KIND_COMPONENT: &str = "component";
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
#[serde(rename_all = "snake_case")]
pub enum RegistryKind {
    Experiment,
    Component,
    Benchmark,
    Workflow,
    Evaluation,
    ExternalEvaluation,
    ResultSchema,
    Study,
    Source,
    Transform,
    Filter,
    Group,
    Dedup,
    Sink,
    Check,
    Metric,
    Pipeline,
    Dataset,
    Adapter,
    Loader,
}

impl RegistryKind {
    pub fn parse(value: &str) -> RlabResult<Self> {
        registry_kind_from_str(value).ok_or_else(|| RlabError::Registry {
            message: format!("{UNKNOWN_REGISTRY_KIND_PREFIX}: {value}"),
        })
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Experiment => KIND_EXPERIMENT,
            Self::Component => KIND_COMPONENT,
            Self::Benchmark => KIND_BENCHMARK,
            Self::Workflow => KIND_WORKFLOW,
            Self::Evaluation => KIND_EVALUATION,
            Self::ExternalEvaluation => KIND_EXTERNAL_EVALUATION,
            Self::ResultSchema => KIND_RESULT_SCHEMA,
            Self::Study => KIND_STUDY,
            Self::Source => KIND_SOURCE,
            Self::Transform => KIND_TRANSFORM,
            Self::Filter => KIND_FILTER,
            Self::Group => KIND_GROUP,
            Self::Dedup => KIND_DEDUP,
            Self::Sink => KIND_SINK,
            Self::Check => KIND_CHECK,
            Self::Metric => KIND_METRIC,
            Self::Pipeline => KIND_PIPELINE,
            Self::Dataset => KIND_DATASET,
            Self::Adapter => KIND_ADAPTER,
            Self::Loader => KIND_LOADER,
        }
    }
}

fn registry_kind_from_str(value: &str) -> Option<RegistryKind> {
    match value {
        KIND_EXPERIMENT => Some(RegistryKind::Experiment),
        KIND_COMPONENT => Some(RegistryKind::Component),
        KIND_BENCHMARK => Some(RegistryKind::Benchmark),
        KIND_WORKFLOW => Some(RegistryKind::Workflow),
        KIND_EVALUATION => Some(RegistryKind::Evaluation),
        KIND_EXTERNAL_EVALUATION => Some(RegistryKind::ExternalEvaluation),
        KIND_RESULT_SCHEMA => Some(RegistryKind::ResultSchema),
        KIND_STUDY => Some(RegistryKind::Study),
        KIND_SOURCE => Some(RegistryKind::Source),
        KIND_TRANSFORM => Some(RegistryKind::Transform),
        KIND_FILTER => Some(RegistryKind::Filter),
        KIND_GROUP => Some(RegistryKind::Group),
        KIND_DEDUP => Some(RegistryKind::Dedup),
        KIND_SINK => Some(RegistryKind::Sink),
        KIND_CHECK => Some(RegistryKind::Check),
        KIND_METRIC => Some(RegistryKind::Metric),
        KIND_PIPELINE => Some(RegistryKind::Pipeline),
        KIND_DATASET => Some(RegistryKind::Dataset),
        KIND_ADAPTER => Some(RegistryKind::Adapter),
        KIND_LOADER => Some(RegistryKind::Loader),
        _ => None,
    }
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
    #[allow(clippy::too_many_arguments)]
    pub fn new(
        kind: RegistryKind,
        name: String,
        version: String,
        module: String,
        qualname: String,
        source: PathBuf,
        tags: Vec<String>,
        description: String,
        metadata: BTreeMap<String, Value>,
    ) -> Self {
        Self::from_args(RegistryRecordArgs {
            kind,
            name,
            version,
            module,
            qualname,
            source,
            tags,
            description,
            metadata,
        })
    }

    fn from_args(args: RegistryRecordArgs) -> Self {
        Self {
            schema_version: REGISTRY_SCHEMA_VERSION,
            kind: args.kind,
            name: args.name,
            version: args.version,
            module: args.module,
            qualname: args.qualname,
            source: args.source,
            tags: args.tags,
            description: args.description,
            metadata: args.metadata,
        }
    }

    fn has_identity(&self, kind: &RegistryKind, name: &str) -> bool {
        self.kind == *kind && self.name == name
    }

    fn identity(&self) -> RegistryRecordIdentity<'_> {
        RegistryRecordIdentity {
            kind: &self.kind,
            name: &self.name,
        }
    }
}

struct RegistryRecordArgs {
    kind: RegistryKind,
    name: String,
    version: String,
    module: String,
    qualname: String,
    source: PathBuf,
    tags: Vec<String>,
    description: String,
    metadata: BTreeMap<String, Value>,
}

struct RegistryRecordIdentity<'a> {
    kind: &'a RegistryKind,
    name: &'a str,
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
            Some(_) => Err(duplicate_record_error(record.identity())),
            None => {
                self.records.push(record);
                Ok(())
            }
        }
    }

    pub fn validate(&self) -> RlabResult<()> {
        for record in &self.records {
            validate_registry_record(record)?;
        }

        Ok(())
    }

    pub fn find(&self, kind: RegistryKind, name: &str) -> Option<&RegistryRecord> {
        self.find_by_identity(&kind, name)
    }

    pub fn records_by_kind(&self, kind: RegistryKind) -> Vec<&RegistryRecord> {
        self.records_by_kind_ref(&kind)
    }

    fn find_existing(&self, record: &RegistryRecord) -> Option<&RegistryRecord> {
        self.find_by_identity(&record.kind, &record.name)
    }

    fn find_by_identity(&self, kind: &RegistryKind, name: &str) -> Option<&RegistryRecord> {
        self.records
            .iter()
            .find(|record| record.has_identity(kind, name))
    }

    fn records_by_kind_ref(&self, kind: &RegistryKind) -> Vec<&RegistryRecord> {
        self.records
            .iter()
            .filter(|record| record.kind == *kind)
            .collect()
    }
}

fn duplicate_record_error(identity: RegistryRecordIdentity<'_>) -> RlabError {
    RlabError::Registry {
        message: format!(
            "{DUPLICATE_REGISTRY_RECORD_PREFIX}: {}:{}",
            identity.kind.as_str(),
            identity.name
        ),
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
        RegistryRecord::new(
            kind,
            name.to_owned(),
            TEST_VERSION.to_owned(),
            TEST_MODULE.to_owned(),
            name.to_owned(),
            source_path(name),
            Vec::new(),
            String::new(),
            BTreeMap::new(),
        )
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
        let record = make_record(RegistryKind::Experiment, "exp1");

        expect_ok(registry.insert(record));

        assert!(registry.find(RegistryKind::Experiment, "exp1").is_some());
        assert!(registry.find(RegistryKind::Experiment, "other").is_none());
    }

    #[test]
    fn insert_duplicate_identical_is_idempotent() {
        let mut registry = Registry::new();
        let record = make_record(RegistryKind::Benchmark, "bench1");

        expect_ok(registry.insert(record.clone()));

        assert!(registry.insert(record).is_ok());
        assert_eq!(registry.records.len(), 1);
    }

    #[test]
    fn insert_duplicate_different_fails() {
        let mut registry = Registry::new();

        expect_ok(registry.insert(make_record(RegistryKind::Experiment, "exp1")));

        let mut conflicting = make_record(RegistryKind::Experiment, "exp1");
        conflicting.version = CONFLICTING_VERSION.to_owned();

        assert!(registry.insert(conflicting).is_err());
    }

    #[test]
    fn registry_kind_parse_valid() {
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_EXPERIMENT)),
            RegistryKind::Experiment
        );
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_BENCHMARK)),
            RegistryKind::Benchmark
        );
        assert_eq!(
            expect_ok(RegistryKind::parse(KIND_DATASET)),
            RegistryKind::Dataset
        );
    }

    #[test]
    fn registry_kind_parse_invalid() {
        assert!(RegistryKind::parse("unknown_kind").is_err());
        assert!(RegistryKind::parse("").is_err());
    }

    #[test]
    fn registry_kind_as_str_roundtrip() {
        for kind in [
            RegistryKind::Experiment,
            RegistryKind::Benchmark,
            RegistryKind::Study,
            RegistryKind::Dataset,
        ] {
            assert_eq!(expect_ok(RegistryKind::parse(kind.as_str())), kind);
        }
    }

    #[test]
    fn records_by_kind_returns_matching_records() {
        let mut registry = Registry::new();

        expect_ok(registry.insert(make_record(RegistryKind::Experiment, "exp1")));
        expect_ok(registry.insert(make_record(RegistryKind::Experiment, "exp2")));
        expect_ok(registry.insert(make_record(RegistryKind::Benchmark, "bench1")));

        let experiments = registry.records_by_kind(RegistryKind::Experiment);

        assert_eq!(experiments.len(), 2);
        assert!(experiments
            .iter()
            .all(|record| record.kind == RegistryKind::Experiment));
    }
}
