use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::validate::validate_registry_record;

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
}

impl RegistryKind {
    pub fn parse(value: &str) -> RlabResult<Self> {
        match value {
            "experiment" => Ok(Self::Experiment),
            "component" => Ok(Self::Component),
            "benchmark" => Ok(Self::Benchmark),
            "workflow" => Ok(Self::Workflow),
            "evaluation" => Ok(Self::Evaluation),
            "external_evaluation" => Ok(Self::ExternalEvaluation),
            "result_schema" => Ok(Self::ResultSchema),
            "study" => Ok(Self::Study),
            "source" => Ok(Self::Source),
            "transform" => Ok(Self::Transform),
            "filter" => Ok(Self::Filter),
            "group" => Ok(Self::Group),
            "dedup" => Ok(Self::Dedup),
            "sink" => Ok(Self::Sink),
            "check" => Ok(Self::Check),
            "metric" => Ok(Self::Metric),
            "pipeline" => Ok(Self::Pipeline),
            "dataset" => Ok(Self::Dataset),
            "adapter" => Ok(Self::Adapter),
            other => Err(RlabError::Registry { message: format!("unknown registry kind: {other}") }),
        }
    }

    pub fn as_str(&self) -> &'static str {
        match self {
            Self::Experiment => "experiment",
            Self::Component => "component",
            Self::Benchmark => "benchmark",
            Self::Workflow => "workflow",
            Self::Evaluation => "evaluation",
            Self::ExternalEvaluation => "external_evaluation",
            Self::ResultSchema => "result_schema",
            Self::Study => "study",
            Self::Source => "source",
            Self::Transform => "transform",
            Self::Filter => "filter",
            Self::Group => "group",
            Self::Dedup => "dedup",
            Self::Sink => "sink",
            Self::Check => "check",
            Self::Metric => "metric",
            Self::Pipeline => "pipeline",
            Self::Dataset => "dataset",
            Self::Adapter => "adapter",
        }
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
        Self {
            schema_version: super::schema::REGISTRY_SCHEMA_VERSION,
            kind,
            name,
            version,
            module,
            qualname,
            source,
            tags,
            description,
            metadata,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Registry {
    pub schema_version: u32,
    pub records: Vec<RegistryRecord>,
}

impl Registry {
    pub fn new() -> Self {
        Self { schema_version: super::schema::REGISTRY_SCHEMA_VERSION, records: Vec::new() }
    }

    pub fn insert(&mut self, record: RegistryRecord) -> RlabResult<()> {
        validate_registry_record(&record)?;
        for existing in &self.records {
            if existing.kind == record.kind && existing.name == record.name {
                if existing == &record {
                    return Ok(());
                }
                return Err(RlabError::Registry { message: format!("duplicate registry record: {}:{}", record.kind.as_str(), record.name) });
            }
        }
        self.records.push(record);
        Ok(())
    }

    pub fn validate(&self) -> RlabResult<()> {
        for record in &self.records {
            validate_registry_record(record)?;
        }
        Ok(())
    }

    pub fn find(&self, kind: RegistryKind, name: &str) -> Option<&RegistryRecord> {
        self.records.iter().find(|record| record.kind == kind && record.name == name)
    }

    pub fn records_by_kind(&self, kind: RegistryKind) -> Vec<&RegistryRecord> {
        self.records.iter().filter(|record| record.kind == kind).collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    fn make_record(kind: RegistryKind, name: &str) -> RegistryRecord {
        RegistryRecord::new(
            kind,
            name.to_string(),
            "0.1.0".to_string(),
            "mymodule".to_string(),
            name.to_string(),
            std::path::PathBuf::from(format!("{name}.py")),
            Vec::new(),
            String::new(),
            BTreeMap::new(),
        )
    }

    #[test]
    fn insert_and_find() {
        let mut registry = Registry::new();
        let record = make_record(RegistryKind::Experiment, "exp1");
        registry.insert(record).unwrap();
        assert!(registry.find(RegistryKind::Experiment, "exp1").is_some());
        assert!(registry.find(RegistryKind::Experiment, "other").is_none());
    }

    #[test]
    fn insert_duplicate_identical_is_idempotent() {
        let mut registry = Registry::new();
        let record = make_record(RegistryKind::Benchmark, "bench1");
        registry.insert(record.clone()).unwrap();
        assert!(registry.insert(record).is_ok());
        assert_eq!(registry.records.len(), 1);
    }

    #[test]
    fn insert_duplicate_different_fails() {
        let mut registry = Registry::new();
        registry.insert(make_record(RegistryKind::Experiment, "exp1")).unwrap();
        let mut conflicting = make_record(RegistryKind::Experiment, "exp1");
        conflicting.version = "1.0.0".to_string();
        assert!(registry.insert(conflicting).is_err());
    }

    #[test]
    fn registry_kind_parse_valid() {
        assert_eq!(RegistryKind::parse("experiment").unwrap(), RegistryKind::Experiment);
        assert_eq!(RegistryKind::parse("benchmark").unwrap(), RegistryKind::Benchmark);
        assert_eq!(RegistryKind::parse("dataset").unwrap(), RegistryKind::Dataset);
    }

    #[test]
    fn registry_kind_parse_invalid() {
        assert!(RegistryKind::parse("unknown_kind").is_err());
        assert!(RegistryKind::parse("").is_err());
    }

    #[test]
    fn registry_kind_as_str_roundtrip() {
        for kind in [RegistryKind::Experiment, RegistryKind::Benchmark, RegistryKind::Study, RegistryKind::Dataset] {
            assert_eq!(RegistryKind::parse(kind.as_str()).unwrap(), kind);
        }
    }
}
