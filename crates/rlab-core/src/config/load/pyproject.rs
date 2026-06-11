use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::error::RlabResult;

use super::super::model::EffectiveConfig;
use super::apply::{
    apply_optional_bool, apply_optional_path, apply_optional_string, apply_optional_vec,
    set_cache_paths,
};
use super::toml::read_optional_toml;

pub const PYPROJECT_FILE: &str = "pyproject.toml";

#[derive(Debug, Deserialize)]
pub struct PyProject {
    pub project: Option<PyProjectSection>,
    pub tool: Option<ToolSection>,
}

#[derive(Debug, Deserialize)]
pub struct PyProjectSection {
    pub name: Option<String>,
}

#[derive(Debug, Deserialize)]
pub struct ToolSection {
    pub rlab: Option<ToolRlabSection>,
}

#[derive(Debug, Deserialize)]
pub struct ToolRlabSection {
    pub name: Option<String>,
    pub modules: Option<Vec<String>>,
    pub runs: Option<PathBuf>,
    pub artifacts: Option<PathBuf>,
    pub cache: Option<PathBuf>,
    pub strict: Option<bool>,
    pub python: Option<String>,
}

pub fn apply_pyproject(root: &Path, config: &mut EffectiveConfig) -> RlabResult<()> {
    let path = root.join(PYPROJECT_FILE);

    let Some(parsed) = read_optional_toml::<PyProject>(&path)? else {
        return Ok(());
    };

    let Some(tool) = parsed.tool else {
        return Ok(());
    };

    let Some(rlab) = tool.rlab else {
        return Ok(());
    };

    apply_optional_string(&mut config.project.name, rlab.name);
    apply_optional_vec(&mut config.python.modules, rlab.modules);
    apply_optional_path(&mut config.paths.runs, rlab.runs);
    apply_optional_path(&mut config.paths.artifacts, rlab.artifacts);

    if let Some(cache) = rlab.cache {
        set_cache_paths(config, cache);
    }

    apply_optional_bool(&mut config.production.strict, rlab.strict);
    apply_optional_string(&mut config.python.executable, rlab.python);

    Ok(())
}
