use std::path::Path;

use crate::error::{RlabError, RlabResult};

use super::super::model::EffectiveConfig;
use super::pyproject::{PyProject, PYPROJECT_FILE};
use super::toml::read_optional_toml;

const CONVENTIONAL_MODULES: &[&str] = &[
    "experiments",
    "workflows",
    "benchmarks",
    "evaluations",
    "components",
];

const PACKAGE_SOURCE_DIR: &str = "src";
const PYTHON_PACKAGE_SEPARATOR: &str = ".";
const PYTHON_MODULE_SEPARATOR: char = '_';
const PROJECT_NAME_SEPARATOR: char = '-';

pub fn infer_project_name(root: &Path) -> RlabResult<String> {
    let pyproject_path = root.join(PYPROJECT_FILE);

    if let Some(pyproject) = read_optional_toml::<PyProject>(&pyproject_path)? {
        if let Some(name) = pyproject_rlab_name(&pyproject) {
            return Ok(name);
        }

        if let Some(name) = pyproject_project_name(pyproject) {
            return Ok(name);
        }
    }

    infer_project_name_from_root(root)
}

pub fn apply_inferred_modules(root: &Path, config: &mut EffectiveConfig) {
    if config.python.modules.is_empty() {
        config.python.modules = infer_modules(root, &config.project.name);
    }
}

fn pyproject_rlab_name(pyproject: &PyProject) -> Option<String> {
    pyproject
        .tool
        .as_ref()
        .and_then(|tool| tool.rlab.as_ref())
        .and_then(|rlab| non_empty_borrowed_string(rlab.name.as_deref()))
}

fn pyproject_project_name(pyproject: PyProject) -> Option<String> {
    pyproject
        .project
        .and_then(|project| non_empty_owned_string(project.name))
}

fn infer_project_name_from_root(root: &Path) -> RlabResult<String> {
    root.file_name()
        .and_then(|name| name.to_str())
        .filter(|name| !name.trim().is_empty())
        .map(str::to_owned)
        .ok_or_else(|| RlabError::Config {
            message: format!("could not infer project name from {}", root.display()),
        })
}

fn infer_modules(root: &Path, project_name: &str) -> Vec<String> {
    let normalized_project_name = normalize_project_name(project_name);

    let mut modules = conventional_root_modules(root);
    modules.extend(package_modules(root, &normalized_project_name));

    modules.sort_unstable();
    modules.dedup();

    modules
}

fn normalize_project_name(project_name: &str) -> String {
    project_name.replace(PROJECT_NAME_SEPARATOR, &PYTHON_MODULE_SEPARATOR.to_string())
}

fn conventional_root_modules(root: &Path) -> Vec<String> {
    CONVENTIONAL_MODULES
        .iter()
        .filter(|module| root.join(module).exists())
        .map(|module| (*module).to_owned())
        .collect()
}

fn package_modules(root: &Path, normalized_project_name: &str) -> Vec<String> {
    CONVENTIONAL_MODULES
        .iter()
        .filter(|module| {
            root.join(PACKAGE_SOURCE_DIR)
                .join(normalized_project_name)
                .join(module)
                .exists()
        })
        .map(|module| {
            [normalized_project_name.to_owned(), (*module).to_owned()]
                .join(PYTHON_PACKAGE_SEPARATOR)
        })
        .collect()
}

fn non_empty_borrowed_string(value: Option<&str>) -> Option<String> {
    value
        .filter(|text| !text.trim().is_empty())
        .map(str::to_owned)
}

fn non_empty_owned_string(value: Option<String>) -> Option<String> {
    value.filter(|text| !text.trim().is_empty())
}
