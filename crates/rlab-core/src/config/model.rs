
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

pub const CONFIG_SCHEMA_VERSION: u32 = 1;

const DEFAULT_RUNS_DIR: &str = ".rlab/runs";
const DEFAULT_ARTIFACTS_DIR: &str = ".rlab/artifacts";
const DEFAULT_CACHE_DIR: &str = ".rlab/cache";
const DEFAULT_REGISTRY_CACHE_FILE: &str = "registry.json";
const DEFAULT_PYTHON_EXECUTABLE: &str = "python";
const DEFAULT_RUNNER_MODULE: &str = "rlab._runner";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EffectiveConfig {
    pub schema_version: u32,
    pub project: ProjectConfig,
    pub paths: PathConfig,
    pub python: PythonConfig,
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
        Self {
            schema_version: CONFIG_SCHEMA_VERSION,
            project: ProjectConfig { name, root },
            paths: PathConfig {
                runs: PathBuf::from(DEFAULT_RUNS_DIR),
                artifacts: PathBuf::from(DEFAULT_ARTIFACTS_DIR),
                cache: cache.clone(),
                registry_cache: cache.join(DEFAULT_REGISTRY_CACHE_FILE),
            },
            python: PythonConfig {
                executable: DEFAULT_PYTHON_EXECUTABLE.to_string(),
                runner_module: DEFAULT_RUNNER_MODULE.to_string(),
                modules: Vec::new(),
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
