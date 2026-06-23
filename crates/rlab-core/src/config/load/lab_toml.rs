use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::Deserialize;
use serde_json::Value;

use crate::error::RlabResult;

use super::super::model::{EffectiveConfig, ResumeStateRetention};
use super::super::validate::validate_lab_schema_version;
use super::apply::{
    apply_optional_bool, apply_optional_path, apply_optional_string, apply_optional_vec,
    set_cache_paths,
};
use super::toml::read_optional_toml;

const LAB_TOML_FILE: &str = "lab.toml";

#[derive(Debug, Deserialize)]
struct LabToml {
    schema_version: Option<u32>,
    project: Option<LabProject>,
    modules: Option<LabModules>,
    paths: Option<LabPaths>,
    python: Option<LabPython>,
    run: Option<LabRun>,
    production: Option<LabProduction>,
    reproducibility: Option<LabReproducibility>,
    storage: Option<LabStorage>,
}

#[derive(Debug, Deserialize)]
struct LabStorage {
    outputs: Option<LabOutputs>,
    runs: Option<LabStorageRuns>,
    materialized: Option<LabMaterialized>,
}

#[derive(Debug, Deserialize)]
struct LabOutputs {
    keep_resume_state: Option<ResumeStateRetention>,
    resume_only_globs: Option<Vec<String>>,
    resume_pointer: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LabStorageRuns {
    keep_per_experiment: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct LabMaterialized {
    max_gb: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct LabProject {
    name: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LabModules {
    load: Option<Vec<String>>,
}

#[derive(Debug, Deserialize)]
struct LabPaths {
    runs: Option<PathBuf>,
    artifacts: Option<PathBuf>,
    cache: Option<PathBuf>,
    registry_cache: Option<PathBuf>,
}

#[derive(Debug, Deserialize)]
struct LabPython {
    modules: Option<Vec<String>>,
    executable: Option<String>,
    runner_module: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LabRun {
    default_seed: Option<u64>,
    params: Option<BTreeMap<String, Value>>,
    env: Option<BTreeMap<String, String>>,
}

#[derive(Debug, Deserialize)]
struct LabProduction {
    strict: Option<bool>,
}

#[derive(Debug, Deserialize)]
struct LabReproducibility {
    capture_git: Option<bool>,
    capture_diff: Option<bool>,
    capture_env: Option<bool>,
    require_clean_git: Option<bool>,
    require_lockfile: Option<bool>,
}

pub fn apply_lab_toml(root: &Path, config: &mut EffectiveConfig) -> RlabResult<()> {
    let path = root.join(LAB_TOML_FILE);

    let Some(parsed) = read_optional_toml::<LabToml>(&path)? else {
        return Ok(());
    };

    validate_lab_schema_version(parsed.schema_version)?;

    apply_project(config, parsed.project);
    apply_modules(config, parsed.modules);

    if let Some(paths) = parsed.paths {
        apply_paths(config, paths);
    }

    if let Some(python) = parsed.python {
        apply_python(config, python);
    }

    if let Some(run) = parsed.run {
        apply_run(config, run);
    }

    if let Some(production) = parsed.production {
        apply_optional_bool(&mut config.production.strict, production.strict);
    }

    if let Some(reproducibility) = parsed.reproducibility {
        apply_reproducibility(config, reproducibility);
    }

    if let Some(storage) = parsed.storage {
        apply_storage(config, storage);
    }

    Ok(())
}

fn apply_storage(config: &mut EffectiveConfig, storage: LabStorage) {
    if let Some(outputs) = storage.outputs {
        if let Some(keep_resume_state) = outputs.keep_resume_state {
            config.storage.outputs.keep_resume_state = keep_resume_state;
        }
        apply_optional_vec(
            &mut config.storage.outputs.resume_only_globs,
            outputs.resume_only_globs,
        );
        apply_optional_string(
            &mut config.storage.outputs.resume_pointer,
            outputs.resume_pointer,
        );
    }
    if let Some(runs) = storage.runs {
        if let Some(keep) = runs.keep_per_experiment {
            config.storage.runs.keep_per_experiment = keep;
        }
    }
    if let Some(materialized) = storage.materialized {
        if let Some(max_gb) = materialized.max_gb {
            config.storage.materialized.max_gb = max_gb;
        }
    }
}

fn apply_project(config: &mut EffectiveConfig, project: Option<LabProject>) {
    if let Some(project) = project {
        apply_optional_string(&mut config.project.name, project.name);
    }
}

fn apply_modules(config: &mut EffectiveConfig, modules: Option<LabModules>) {
    if let Some(modules) = modules {
        apply_optional_vec(&mut config.python.modules, modules.load);
    }
}

fn apply_paths(config: &mut EffectiveConfig, paths: LabPaths) {
    apply_optional_path(&mut config.paths.runs, paths.runs);
    apply_optional_path(&mut config.paths.artifacts, paths.artifacts);

    if let Some(cache) = paths.cache {
        set_cache_paths(config, cache);
    }

    apply_optional_path(&mut config.paths.registry_cache, paths.registry_cache);
}

fn apply_python(config: &mut EffectiveConfig, python: LabPython) {
    apply_optional_vec(&mut config.python.modules, python.modules);
    apply_optional_string(&mut config.python.executable, python.executable);
    apply_optional_string(&mut config.python.runner_module, python.runner_module);
}

fn apply_run(config: &mut EffectiveConfig, run: LabRun) {
    if run.default_seed.is_some() {
        config.run.default_seed = run.default_seed;
    }
    if let Some(params) = run.params {
        config.run.params = params;
    }
    if let Some(env) = run.env {
        config.run.env = env;
    }
}

fn apply_reproducibility(config: &mut EffectiveConfig, reproducibility: LabReproducibility) {
    apply_optional_bool(
        &mut config.reproducibility.capture_git,
        reproducibility.capture_git,
    );
    apply_optional_bool(
        &mut config.reproducibility.capture_diff,
        reproducibility.capture_diff,
    );
    apply_optional_bool(
        &mut config.reproducibility.capture_env,
        reproducibility.capture_env,
    );
    apply_optional_bool(
        &mut config.reproducibility.require_clean_git,
        reproducibility.require_clean_git,
    );
    apply_optional_bool(
        &mut config.reproducibility.require_lockfile,
        reproducibility.require_lockfile,
    );
}
