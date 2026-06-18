use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};
use serde_json::Value;

pub const CONFIG_SCHEMA_VERSION: u32 = 1;

pub const DEFAULT_RUNS_DIR: &str = ".rlab/runs";
pub const DEFAULT_ARTIFACTS_DIR: &str = ".rlab/artifacts";
pub const DEFAULT_CACHE_DIR: &str = ".rlab/cache";
pub const DEFAULT_REGISTRY_CACHE_FILE: &str = "registry.json";
pub const DEFAULT_PYTHON_EXECUTABLE: &str = "python";
pub const DEFAULT_RUNNER_MODULE: &str = "rlab._runner";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectiveConfig {
    pub schema_version: u32,
    pub project: ProjectConfig,
    pub paths: PathConfig,
    pub python: PythonConfig,
    pub run: RunConfig,
    pub production: ProductionConfig,
    pub reproducibility: ReproducibilityConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectConfig {
    pub name: String,
    pub root: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PathConfig {
    pub runs: PathBuf,
    pub artifacts: PathBuf,
    pub cache: PathBuf,
    pub registry_cache: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonConfig {
    pub executable: String,
    pub runner_module: String,
    pub modules: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunConfig {
    pub default_seed: Option<u64>,
    pub params: BTreeMap<String, Value>,
    pub env: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProductionConfig {
    pub strict: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ReproducibilityConfig {
    pub capture_git: bool,
    pub capture_diff: bool,
    pub capture_env: bool,
    pub require_clean_git: bool,
    pub require_lockfile: bool,
}

impl EffectiveConfig {
    pub fn default_for(root: PathBuf, name: String) -> Self {
        let cache = PathBuf::from(DEFAULT_CACHE_DIR);
        let registry_cache = cache.join(DEFAULT_REGISTRY_CACHE_FILE);

        Self {
            schema_version: CONFIG_SCHEMA_VERSION,
            project: ProjectConfig { name, root },
            paths: PathConfig {
                runs: PathBuf::from(DEFAULT_RUNS_DIR),
                artifacts: PathBuf::from(DEFAULT_ARTIFACTS_DIR),
                cache,
                registry_cache,
            },
            python: PythonConfig {
                executable: DEFAULT_PYTHON_EXECUTABLE.to_owned(),
                runner_module: DEFAULT_RUNNER_MODULE.to_owned(),
                modules: Vec::new(),
            },
            run: RunConfig {
                default_seed: None,
                params: BTreeMap::new(),
                env: BTreeMap::new(),
            },
            production: ProductionConfig { strict: false },
            reproducibility: ReproducibilityConfig {
                capture_git: true,
                capture_diff: true,
                capture_env: true,
                require_clean_git: false,
                require_lockfile: false,
            },
        }
    }
}
