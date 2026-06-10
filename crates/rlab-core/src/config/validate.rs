
use std::fs;
use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::error::{RlabError, RlabResult};

use super::discovery::find_project_root;
use super::env::rlab_environment;
use super::model::{EffectiveConfig, CONFIG_SCHEMA_VERSION};
use super::overrides::ConfigOverride;

#[derive(Debug, Deserialize)]
struct PyProject {
    project: Option<PyProjectSection>,
    tool: Option<ToolSection>,
}

#[derive(Debug, Deserialize)]
struct PyProjectSection {
    name: Option<String>,
}

#[derive(Debug, Deserialize)]
struct ToolSection {
    rlab: Option<ToolRlabSection>,
}

#[derive(Debug, Deserialize)]
struct ToolRlabSection {
    name: Option<String>,
    modules: Option<Vec<String>>,
    runs: Option<PathBuf>,
    artifacts: Option<PathBuf>,
    cache: Option<PathBuf>,
    strict: Option<bool>,
    python: Option<String>,
}

#[derive(Debug, Deserialize)]
struct LabToml {
    schema_version: Option<u32>,
    project: Option<LabProject>,
    modules: Option<LabModules>,
    paths: Option<LabPaths>,
    python: Option<LabPython>,
    production: Option<LabProduction>,
    reproducibility: Option<LabReproducibility>,
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

pub fn load_effective_config(root: Option<&Path>, overrides: &[ConfigOverride]) -> RlabResult<EffectiveConfig> {
    let start = match root {
        Some(path) => path.to_path_buf(),
        None => std::env::current_dir().map_err(|error| RlabError::io(Path::new("."), error))?,
    };
    let project_root = find_project_root(&start)?;
    let project_name = infer_project_name(&project_root)?;
    let mut config = EffectiveConfig::default_for(project_root.clone(), project_name);
    apply_pyproject(&project_root, &mut config)?;
    apply_lab_toml(&project_root, &mut config)?;
    apply_environment(&mut config)?;
    apply_overrides(&mut config, overrides)?;
    if config.python.modules.is_empty() {
        config.python.modules = infer_modules(&project_root, &config.project.name);
    }
    validate_config(&config)?;
    Ok(config)
}

fn infer_project_name(root: &Path) -> RlabResult<String> {
    let pyproject = root.join("pyproject.toml");
    if pyproject.exists() {
        let content = fs::read_to_string(&pyproject).map_err(|error| RlabError::io(&pyproject, error))?;
        let parsed: PyProject = toml::from_str(&content).map_err(RlabError::serialization)?;
        if let Some(tool) = &parsed.tool {
            if let Some(rlab) = &tool.rlab {
                if let Some(name) = &rlab.name {
                    if !name.trim().is_empty() {
                        return Ok(name.clone());
                    }
                }
            }
        }
        if let Some(project) = parsed.project {
            if let Some(name) = project.name {
                if !name.trim().is_empty() {
                    return Ok(name);
                }
            }
        }
    }
    root.file_name()
        .and_then(|name| name.to_str())
        .map(std::string::ToString::to_string)
        .ok_or_else(|| RlabError::Config {
            message: format!("could not infer project name from {}", root.display()),
        })
}

fn apply_pyproject(root: &Path, config: &mut EffectiveConfig) -> RlabResult<()> {
    let path = root.join("pyproject.toml");
    if !path.exists() {
        return Ok(());
    }
    let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
    let parsed: PyProject = toml::from_str(&content).map_err(RlabError::serialization)?;
    if let Some(tool) = parsed.tool {
        if let Some(rlab) = tool.rlab {
            if let Some(name) = rlab.name {
                config.project.name = name;
            }
            if let Some(modules) = rlab.modules {
                config.python.modules = modules;
            }
            if let Some(runs) = rlab.runs {
                config.paths.runs = runs;
            }
            if let Some(artifacts) = rlab.artifacts {
                config.paths.artifacts = artifacts;
            }
            if let Some(cache) = rlab.cache {
                config.paths.cache = cache.clone();
                config.paths.registry_cache = cache.join("registry.json");
            }
            if let Some(strict) = rlab.strict {
                config.production.strict = strict;
            }
            if let Some(python) = rlab.python {
                config.python.executable = python;
            }
        }
    }
    Ok(())
}

fn apply_lab_toml(root: &Path, config: &mut EffectiveConfig) -> RlabResult<()> {
    let path = root.join("lab.toml");
    if !path.exists() {
        return Ok(());
    }
    let content = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
    let parsed: LabToml = toml::from_str(&content).map_err(RlabError::serialization)?;
    if let Some(version) = parsed.schema_version {
        if version != CONFIG_SCHEMA_VERSION {
            return Err(RlabError::Config { message: format!("unsupported lab.toml schema_version: {version}") });
        }
    }
    if let Some(project) = parsed.project {
        if let Some(name) = project.name {
            config.project.name = name;
        }
    }
    if let Some(modules) = parsed.modules {
        if let Some(load) = modules.load {
            config.python.modules = load;
        }
    }
    if let Some(paths) = parsed.paths {
        if let Some(runs) = paths.runs {
            config.paths.runs = runs;
        }
        if let Some(artifacts) = paths.artifacts {
            config.paths.artifacts = artifacts;
        }
        if let Some(cache) = paths.cache {
            config.paths.cache = cache.clone();
            config.paths.registry_cache = cache.join("registry.json");
        }
        if let Some(registry_cache) = paths.registry_cache {
            config.paths.registry_cache = registry_cache;
        }
    }
    if let Some(python) = parsed.python {
        if let Some(modules) = python.modules {
            config.python.modules = modules;
        }
        if let Some(executable) = python.executable {
            config.python.executable = executable;
        }
        if let Some(runner_module) = python.runner_module {
            config.python.runner_module = runner_module;
        }
    }
    if let Some(production) = parsed.production {
        if let Some(strict) = production.strict {
            config.production.strict = strict;
        }
    }
    if let Some(repro) = parsed.reproducibility {
        if let Some(value) = repro.capture_git { config.reproducibility.capture_git = value; }
        if let Some(value) = repro.capture_diff { config.reproducibility.capture_diff = value; }
        if let Some(value) = repro.capture_env { config.reproducibility.capture_env = value; }
        if let Some(value) = repro.require_clean_git { config.reproducibility.require_clean_git = value; }
        if let Some(value) = repro.require_lockfile { config.reproducibility.require_lockfile = value; }
    }
    Ok(())
}

fn apply_environment(config: &mut EffectiveConfig) -> RlabResult<()> {
    for (key, value) in rlab_environment() {
        match key.as_str() {
            "RLAB__PRODUCTION__STRICT" => config.production.strict = parse_bool(&value)?,
            "RLAB__PYTHON__EXECUTABLE" => config.python.executable = value,
            "RLAB__PYTHON__RUNNER_MODULE" => config.python.runner_module = value,
            "RLAB__PATHS__RUNS" => config.paths.runs = PathBuf::from(value),
            "RLAB__PATHS__ARTIFACTS" => config.paths.artifacts = PathBuf::from(value),
            "RLAB__PATHS__CACHE" => {
                config.paths.cache = PathBuf::from(&value);
                config.paths.registry_cache = PathBuf::from(value).join("registry.json");
            }
            _ => {}
        }
    }
    Ok(())
}

fn apply_overrides(config: &mut EffectiveConfig, overrides: &[ConfigOverride]) -> RlabResult<()> {
    for override_value in overrides {
        let path = override_value.path.join(".");
        match path.as_str() {
            "production.strict" => {
                let value = override_value.value.as_bool().ok_or_else(|| RlabError::Config {
                    message: "production.strict override must be a boolean".to_string(),
                })?;
                config.production.strict = value;
            }
            "python.executable" => config.python.executable = value_as_string(&override_value.value, &path)?,
            "python.runner_module" => config.python.runner_module = value_as_string(&override_value.value, &path)?,
            "paths.runs" => config.paths.runs = PathBuf::from(value_as_string(&override_value.value, &path)?),
            "paths.artifacts" => config.paths.artifacts = PathBuf::from(value_as_string(&override_value.value, &path)?),
            "paths.cache" => {
                let cache = PathBuf::from(value_as_string(&override_value.value, &path)?);
                config.paths.cache = cache.clone();
                config.paths.registry_cache = cache.join("registry.json");
            }
            _ => return Err(RlabError::Config { message: format!("unknown override path: {path}") }),
        }
    }
    Ok(())
}

fn value_as_string(value: &serde_json::Value, path: &str) -> RlabResult<String> {
    match value.as_str() {
        Some(text) if !text.trim().is_empty() => Ok(text.to_string()),
        _ => Err(RlabError::Config { message: format!("{path} override must be a non-empty string") }),
    }
}

fn parse_bool(value: &str) -> RlabResult<bool> {
    match value {
        "1" | "true" | "TRUE" | "yes" | "YES" => Ok(true),
        "0" | "false" | "FALSE" | "no" | "NO" => Ok(false),
        _ => Err(RlabError::Config { message: format!("invalid boolean value: {value}") }),
    }
}

fn infer_modules(root: &Path, project_name: &str) -> Vec<String> {
    let conventional = ["experiments", "workflows", "benchmarks", "evaluations", "components"];
    let mut modules: Vec<String> = conventional
        .iter()
        .filter(|name| root.join(name).exists())
        .map(|name| (*name).to_string())
        .collect();
    let normalized = project_name.replace('-', "_");
    for module in ["experiments", "workflows", "benchmarks", "evaluations", "components"] {
        let package_module = root.join("src").join(&normalized).join(module);
        if package_module.exists() {
            modules.push(format!("{normalized}.{module}"));
        }
    }
    modules.sort();
    modules.dedup();
    modules
}

fn validate_config(config: &EffectiveConfig) -> RlabResult<()> {
    if config.project.name.trim().is_empty() {
        return Err(RlabError::Config { message: "project name cannot be empty".to_string() });
    }
    if config.schema_version != CONFIG_SCHEMA_VERSION {
        return Err(RlabError::Config { message: "unsupported config schema version".to_string() });
    }
    if config.python.executable.trim().is_empty() {
        return Err(RlabError::Config { message: "python executable cannot be empty".to_string() });
    }
    if config.python.runner_module.trim().is_empty() {
        return Err(RlabError::Config { message: "python runner module cannot be empty".to_string() });
    }
    Ok(())
}
