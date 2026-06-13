use std::collections::BTreeMap;
use std::fs;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{RlabError, RlabResult};
use crate::fs::write_json_atomic;

use super::{Registry, RegistryRecord};

pub const REGISTRY_SCHEMA_VERSION: u32 = 1;

const HASH_SEPARATOR: [u8; 1] = [0];
const HASH_BUFFER_SIZE: usize = 64 * 1024;

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
        Ok(Self {
            schema_version: REGISTRY_SCHEMA_VERSION,
            rlab_version: key.rlab_version.clone(),
            config_hash: key.config_hash.clone(),
            module_hash: hash_strings(&key.modules),
            source_hashes: source_hashes(&key.source_paths)?,
            python_executable: key.python_executable.clone(),
            python_version: key.python_version.clone(),
            strict_policy_hash: key.strict_policy_hash.clone(),
            records: registry.records,
        })
    }

    pub fn into_registry(self) -> Registry {
        Registry {
            schema_version: REGISTRY_SCHEMA_VERSION,
            records: self.records,
        }
    }

    pub fn is_valid_for(&self, key: &RegistryCacheKey) -> RlabResult<bool> {
        if self.schema_version != REGISTRY_SCHEMA_VERSION {
            return Ok(false);
        }

        if !self.metadata_matches(key) {
            return Ok(false);
        }

        sources_match(&self.source_hashes, &key.source_paths)
    }

    fn metadata_matches(&self, key: &RegistryCacheKey) -> bool {
        self.rlab_version == key.rlab_version
            && self.config_hash == key.config_hash
            && self.module_hash == hash_strings(&key.modules)
            && self.python_executable == key.python_executable
            && self.python_version == key.python_version
            && self.strict_policy_hash == key.strict_policy_hash
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

pub fn save_registry_cache(
    path: &Path,
    registry: Registry,
    key: &RegistryCacheKey,
) -> RlabResult<()> {
    let cache = RegistryCache::from_registry(registry, key)?;
    write_json_atomic(path, &cache)
}

pub fn hash_strings(values: &[String]) -> String {
    let mut hasher = Sha256::new();

    for value in values {
        hasher.update(value.as_bytes());
        hasher.update(HASH_SEPARATOR);
    }

    hex::encode(hasher.finalize())
}

pub fn hash_file(path: &Path) -> RlabResult<String> {
    let file = fs::File::open(path).map_err(|error| RlabError::io(path, error))?;
    let mut reader = BufReader::with_capacity(HASH_BUFFER_SIZE, file);
    let mut buffer = [0u8; HASH_BUFFER_SIZE];
    let mut hasher = Sha256::new();

    loop {
        let bytes_read = reader
            .read(&mut buffer)
            .map_err(|error| RlabError::io(path, error))?;

        if bytes_read == 0 {
            break;
        }

        hasher.update(&buffer[..bytes_read]);
    }

    Ok(hex::encode(hasher.finalize()))
}

fn source_hashes(paths: &[PathBuf]) -> RlabResult<BTreeMap<PathBuf, String>> {
    let mut hashes = BTreeMap::new();

    for path in paths {
        if path.is_file() {
            hashes.insert(path.clone(), hash_file(path)?);
        }
    }

    Ok(hashes)
}

fn sources_match(
    cached_hashes: &BTreeMap<PathBuf, String>,
    source_paths: &[PathBuf],
) -> RlabResult<bool> {
    for path in source_paths {
        if path.is_file() && !source_matches(cached_hashes, path)? {
            return Ok(false);
        }
    }

    Ok(true)
}

fn source_matches(cached_hashes: &BTreeMap<PathBuf, String>, path: &Path) -> RlabResult<bool> {
    let current = hash_file(path)?;

    match cached_hashes.get(path) {
        Some(cached) => Ok(cached == &current),
        None => Ok(false),
    }
}
