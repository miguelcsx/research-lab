use std::path::PathBuf;

use serde::{Deserialize, Serialize};

const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileArtifact {
    pub schema_version: u32,
    pub name: String,
    pub path: PathBuf,
    pub version: String,
}

impl FileArtifact {
    pub fn new(name: String, path: PathBuf, version: String) -> Self {
        Self { schema_version: SCHEMA_VERSION, name, path, version }
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
        Self { schema_version: SCHEMA_VERSION, name, path }
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
        Self { schema_version: SCHEMA_VERSION, name, path }
    }
}
