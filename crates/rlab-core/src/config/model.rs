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
    #[serde(default)]
    pub storage: StorageConfig,
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

/// Automatic storage management applied when a run completes.
///
/// rlab is a general research runtime, so the universally safe, content-agnostic
/// behavior is always on (content deduplication, sweeping unreachable objects,
/// bounding the materialized cache) and needs no configuration. The opinionated,
/// domain-specific policies — discarding regenerable "resume-only" output files
/// and pruning old run directories — are opt-in and default to off, because only
/// a project knows which of its outputs are disposable. A project declares those
/// once in its own `lab.toml`.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct StorageConfig {
    pub outputs: OutputRetention,
    pub runs: RunRetention,
    pub materialized: MaterializedRetention,
}

/// Retention policy for a run's directory outputs. Outputs promoted to the
/// content-addressed store are always preserved and deduplicated; this policy only
/// governs "resume-only" files — large files needed solely to resume/continue a
/// computation (e.g. optimizer or solver state) rather than to consume its result.
/// Empty `resume_only_globs` (the default) disables this entirely.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OutputRetention {
    /// Which copies keep their resume-only files.
    pub keep_resume_state: ResumeStateRetention,
    /// Glob patterns (matched against the file name) marking resume-only files.
    /// Empty means nothing is treated as resume-only.
    pub resume_only_globs: Vec<String>,
    /// File inside a run's `outputs/` naming the resumable copy, if the project
    /// writes one. Empty falls back to the most recently modified copy.
    pub resume_pointer: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
#[serde(rename_all = "lowercase")]
pub enum ResumeStateRetention {
    /// Keep resume-only files only on the resumable copy; strip them elsewhere.
    #[default]
    Last,
    /// Keep resume-only files on every copy.
    All,
    /// Strip resume-only files from every copy, including the resumable one.
    None,
}

impl Default for OutputRetention {
    fn default() -> Self {
        Self {
            keep_resume_state: ResumeStateRetention::Last,
            resume_only_globs: Vec::new(),
            resume_pointer: String::new(),
        }
    }
}

/// Retention policy for completed run directories.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RunRetention {
    /// Keep at most this many recent runs per experiment name; `0` (default)
    /// disables pruning. Only runs whose durable outputs are already in the store
    /// are eligible, so lightweight runs are never lost.
    pub keep_per_experiment: u32,
}

/// Bound on the regenerable `materialized/` cache.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaterializedRetention {
    /// Evict least-recently-used entries above this size in GiB; `0` disables eviction.
    pub max_gb: u32,
}

impl Default for MaterializedRetention {
    fn default() -> Self {
        Self { max_gb: 20 }
    }
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
            storage: StorageConfig::default(),
        }
    }
}
