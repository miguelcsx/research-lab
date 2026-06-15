use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileArtifact {
    pub schema_version: u32,
    pub name: String,
    pub path: PathBuf,
    pub kind: String,
    pub version: String,
    pub metadata: BTreeMap<String, Value>,
}

impl FileArtifact {
    pub fn new(name: String, path: PathBuf, version: String) -> Self {
        Self::new_typed(name, path, "file".to_string(), version, BTreeMap::new())
    }

    pub fn new_typed(
        name: String,
        path: PathBuf,
        kind: String,
        version: String,
        metadata: BTreeMap<String, Value>,
    ) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            name,
            path,
            kind,
            version,
            metadata,
        }
    }

    pub fn event_payload(&self) -> Value {
        json!({
            "schema_version": self.schema_version,
            "kind": self.kind,
            "name": self.name,
            "path": self.path,
            "version": self.version,
            "metadata": self.metadata,
        })
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TableArtifact {
    pub schema_version: u32,
    pub name: String,
    pub path: PathBuf,
}

impl TableArtifact {
    pub fn new(name: String, path: PathBuf) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            name,
            path,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogArtifact {
    pub schema_version: u32,
    pub name: String,
    pub path: PathBuf,
}

impl LogArtifact {
    pub fn new(name: String, path: PathBuf) -> Self {
        Self {
            schema_version: SCHEMA_VERSION,
            name,
            path,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResultSchema {
    pub name: String,
    pub fields: BTreeMap<String, String>,
    pub version: String,
}

impl ResultSchema {
    pub fn new(name: String, fields: BTreeMap<String, String>, version: String) -> Self {
        Self {
            name,
            fields,
            version,
        }
    }
}
