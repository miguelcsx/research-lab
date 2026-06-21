use std::{fs, path::Path};

use crate::error::{RlabError, RlabResult};

use super::super::model::EffectiveConfig;
use super::pyproject::{PyProject, PYPROJECT_FILE};
use super::toml::read_optional_toml;

const CONVENTIONAL_MODULES: &[&str] = &[
    "experiments",
    "workflows",
    "benchmarks",
    "evaluations",
];

const PACKAGE_SOURCE_DIR: &str = "src";
const PYTHON_PACKAGE_SEPARATOR: &str = ".";
const PYTHON_MODULE_SEPARATOR: char = '_';
const PROJECT_NAME_SEPARATOR: char = '-';
const PYTHON_PACKAGE_MARKER: &str = "__init__.py";
const IGNORED_TOP_LEVEL_PACKAGES: &[&str] = &[
    "tests",
    "test",
    "external",
    "inspo",
    "scripts",
    "docs",
    "artifacts",
];

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
    modules.extend(top_level_packages(root));
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

fn top_level_packages(root: &Path) -> Vec<String> {
    let Ok(entries) = fs::read_dir(root) else {
        return Vec::new();
    };
    entries
        .flatten()
        .filter_map(|entry| top_level_package_name(&entry.path()))
        .collect()
}

fn top_level_package_name(path: &Path) -> Option<String> {
    if !path.join(PYTHON_PACKAGE_MARKER).exists() {
        return None;
    }
    let name = path.file_name()?.to_str()?;
    if name.starts_with('.') || name.starts_with('_') || IGNORED_TOP_LEVEL_PACKAGES.contains(&name)
    {
        return None;
    }
    Some(name.to_owned())
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

#[cfg(test)]
mod tests {
    use std::{
        fs,
        path::{Path, PathBuf},
        time::{SystemTime, UNIX_EPOCH},
    };

    use super::infer_modules;

    fn package(root: &Path, name: &str) {
        let path = root.join(name);
        fs::create_dir_all(&path).unwrap();
        fs::write(path.join("__init__.py"), "").unwrap();
    }

    fn temp_root() -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let root = std::env::temp_dir().join(format!("rlab-infer-test-{nanos}"));
        fs::create_dir_all(&root).unwrap();
        root
    }

    #[test]
    fn infers_top_level_python_packages() {
        let root = temp_root();
        package(&root, "models");
        package(&root, "tokenization");
        package(&root, "tests");
        fs::create_dir_all(root.join("not_a_package")).unwrap();

        assert_eq!(
            infer_modules(&root, "project"),
            vec!["models".to_string(), "tokenization".to_string()]
        );

        fs::remove_dir_all(root).unwrap();
    }
}

fn non_empty_borrowed_string(value: Option<&str>) -> Option<String> {
    value
        .filter(|text| !text.trim().is_empty())
        .map(str::to_owned)
}

fn non_empty_owned_string(value: Option<String>) -> Option<String> {
    value.filter(|text| !text.trim().is_empty())
}
