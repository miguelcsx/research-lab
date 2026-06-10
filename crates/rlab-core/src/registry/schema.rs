use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{RlabError, RlabResult};
use crate::fs::write_json_atomic;

use super::{Registry, RegistryRecord};

pub const REGISTRY_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RegistryCache {
    pub schema_version: u32,
    pub rlab_version: String,
    pub config_hash: String,
    pub module_hash: String,
    pub source_hashes: BTreeMap<PathBuf, String>,
    pub python_executable: String,
    pub python_version: String,
    pub strict_policy_hash: String,
    pub records: Vec<RegistryRecord>,
}

#[derive(Debug, Clone)]
pub struct RegistryCacheKey {
    pub rlab_version: String,
    pub config_hash: String,
    pub modules: Vec<String>,
    pub source_paths: Vec<PathBuf>,
    pub python_executable: String,
    pub python_version: String,
    pub strict_policy_hash: String,
}

impl RegistryCache {
    pub fn from_registry(registry: Registry, key: &RegistryCacheKey) -> RlabResult<Self> {
        let mut source_hashes = BTreeMap::new();
        for path in &key.source_paths {
            if path.is_file() {
                source_hashes.insert(path.clone(), hash_file(path)?);
            }
        }
        Ok(Self {
            schema_version: REGISTRY_SCHEMA_VERSION,
            rlab_version: key.rlab_version.clone(),
            config_hash: key.config_hash.clone(),
            module_hash: hash_strings(&key.modules),
            source_hashes,
            python_executable: key.python_executable.clone(),
            python_version: key.python_version.clone(),
            strict_policy_hash: key.strict_policy_hash.clone(),
            records: registry.records,
        })
    }

    pub fn into_registry(self) -> Registry {
        Registry { schema_version: REGISTRY_SCHEMA_VERSION, records: self.records }
    }

    pub fn is_valid_for(&self, key: &RegistryCacheKey) -> RlabResult<bool> {
        if self.schema_version != REGISTRY_SCHEMA_VERSION {
            return Ok(false);
        }
        if self.rlab_version != key.rlab_version
            || self.config_hash != key.config_hash
            || self.module_hash != hash_strings(&key.modules)
            || self.python_executable != key.python_executable
            || self.python_version != key.python_version
            || self.strict_policy_hash != key.strict_policy_hash
        {
            return Ok(false);
        }
        for path in &key.source_paths {
            if path.is_file() {
                let current = hash_file(path)?;
                match self.source_hashes.get(path) {
                    Some(cached) if cached == &current => {}
                    _ => return Ok(false),
                }
            }
        }
        Ok(true)
    }
}

pub fn load_registry_cache(path: &Path, key: &RegistryCacheKey) -> RlabResult<Option<Registry>> {
    if !path.exists() {
        return Ok(None);
    }
    let content = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    let cache: RegistryCache = serde_json::from_str(&content).map_err(RlabError::serialization)?;
    if cache.is_valid_for(key)? {
        return Ok(Some(cache.into_registry()));
    }
    Ok(None)
}

pub fn save_registry_cache(path: &Path, registry: Registry, key: &RegistryCacheKey) -> RlabResult<()> {
    let cache = RegistryCache::from_registry(registry, key)?;
    write_json_atomic(path, &cache)
}

pub fn hash_strings(values: &[String]) -> String {
    let mut hasher = Sha256::new();
    for value in values {
        hasher.update(value.as_bytes());
        hasher.update([0]);
    }
    hex::encode(hasher.finalize())
}

pub fn hash_file(path: &Path) -> RlabResult<String> {
    let bytes = fs::read(path).map_err(|error| RlabError::io(path, error))?;
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    Ok(hex::encode(hasher.finalize()))
}
