use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};

use serde_json::Value;

use crate::error::{RlabError, RlabResult};

use super::merge::merge;
use super::overrides::set_path;
use super::ResolvedDocument;

pub fn resolve_document(
    root: &Path,
    name: &str,
    suffix: &str,
    overrides: BTreeMap<String, Value>,
    require_explicit_paths: bool,
) -> RlabResult<ResolvedDocument> {
    let mut value = load(root, name, suffix, &mut Vec::new())?;

    apply_overrides(&mut value, &overrides, require_explicit_paths)?;

    Ok(ResolvedDocument {
        name: name.to_string(),
        source: document_path(root, name, suffix)?,
        value,
        overrides,
    })
}

pub fn list_documents(root: &Path, suffix: &str) -> RlabResult<Vec<String>> {
    let mut names = Vec::new();

    for entry in read_dir(root)? {
        let path = entry.map_err(|error| RlabError::io(root, error))?.path();

        if let Some(name) = document_name(&path, suffix) {
            names.push(name.to_string());
        }
    }

    names.sort();

    Ok(names)
}

pub fn validate_documents(root: &Path, suffix: &str) -> RlabResult<BTreeMap<String, String>> {
    let mut failures = BTreeMap::new();

    for name in list_documents(root, suffix)? {
        if let Err(error) = resolve_document(root, &name, suffix, BTreeMap::new(), true) {
            failures.insert(name, error.to_string());
        }
    }

    Ok(failures)
}

fn apply_overrides(
    value: &mut Value,
    overrides: &BTreeMap<String, Value>,
    require_explicit_paths: bool,
) -> RlabResult<()> {
    for (path, override_value) in overrides {
        if require_explicit_paths && !path.contains('.') {
            return Err(RlabError::config(format!(
                "override {path:?} must use an explicit dotted path"
            )));
        }

        set_path(value, path, override_value.clone())?;
    }

    Ok(())
}

fn load(root: &Path, name: &str, suffix: &str, stack: &mut Vec<String>) -> RlabResult<Value> {
    validate_not_cyclic(name, stack)?;

    let path = document_path(root, name, suffix)?;
    let mut current = read_yaml_document(&path)?;
    let parent = remove_parent(&mut current, &path)?;

    let Some(parent) = parent else {
        return Ok(current);
    };

    stack.push(name.to_string());
    let base = load(root, &parent, suffix, stack);
    stack.pop();

    Ok(merge(base?, current))
}

fn validate_not_cyclic(name: &str, stack: &[String]) -> RlabResult<()> {
    if !stack.iter().any(|value| value == name) {
        return Ok(());
    }

    let mut chain = Vec::with_capacity(stack.len() + 1);
    chain.extend(stack.iter().map(String::as_str));
    chain.push(name);

    Err(RlabError::config(format!(
        "cyclic config inheritance: {}",
        chain.join(" -> ")
    )))
}

fn read_yaml_document(path: &Path) -> RlabResult<Value> {
    let text = fs::read_to_string(path).map_err(|error| RlabError::io(path, error))?;
    let yaml: serde_yaml::Value = serde_yaml::from_str(&text).map_err(RlabError::serialization)?;

    serde_json::to_value(yaml).map_err(RlabError::serialization)
}

fn remove_parent(current: &mut Value, path: &Path) -> RlabResult<Option<String>> {
    let object = current.as_object_mut().ok_or_else(|| {
        RlabError::config(format!(
            "config document must be a mapping: {}",
            path.display()
        ))
    })?;

    let Some(parent) = object.remove("extends") else {
        return Ok(None);
    };

    match parent.as_str().filter(|value| !value.is_empty()) {
        Some(s) => Ok(Some(s.to_owned())),
        None => Err(RlabError::config(format!(
            "config extends must be a non-empty string: {}",
            path.display()
        ))),
    }
}

fn document_path(root: &Path, name: &str, suffix: &str) -> RlabResult<PathBuf> {
    validate_document_name(name)?;

    let path = root.join(format!("{name}{suffix}"));

    if path.is_file() {
        return Ok(path);
    }

    Err(RlabError::config(format!(
        "config not found: {}",
        path.display()
    )))
}

fn validate_document_name(name: &str) -> RlabResult<()> {
    if !name.is_empty() && !name.starts_with('.') && !contains_path_separator(name) {
        return Ok(());
    }

    Err(RlabError::config(format!("invalid config name: {name:?}")))
}

fn contains_path_separator(value: &str) -> bool {
    value.contains('/') || value.contains('\\')
}

fn read_dir(path: &Path) -> RlabResult<fs::ReadDir> {
    fs::read_dir(path).map_err(|error| RlabError::io(path, error))
}

fn document_name<'a>(path: &'a Path, suffix: &str) -> Option<&'a str> {
    if !path.is_file() {
        return None;
    }

    path.file_name()
        .and_then(|value| value.to_str())
        .and_then(|value| value.strip_suffix(suffix))
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    fn temp_dir() -> PathBuf {
        let unique = match SystemTime::now().duration_since(UNIX_EPOCH) {
            Ok(duration) => duration.as_nanos(),
            Err(error) => panic!("system clock is before UNIX_EPOCH: {error}"),
        };

        let path = std::env::temp_dir().join(format!("rlab-configs-{unique}"));

        expect_ok(fs::create_dir_all(&path).map_err(|error| {
            RlabError::config(format!("failed to create temporary config dir: {error}"))
        }));

        path
    }

    #[test]
    fn resolves_extends_and_dotted_overrides() {
        let root = temp_dir();

        expect_ok(
            fs::write(root.join("base.yaml"), "model:\n  width: 32\n").map_err(|error| {
                RlabError::config(format!("failed to write base config: {error}"))
            }),
        );

        expect_ok(
            fs::write(
                root.join("child.yaml"),
                "extends: base\nmodel:\n  layers: 2\n",
            )
            .map_err(|error| RlabError::config(format!("failed to write child config: {error}"))),
        );

        let document = expect_ok(resolve_document(
            &root,
            "child",
            ".yaml",
            BTreeMap::from([("model.width".to_string(), Value::from(64))]),
            true,
        ));

        assert_eq!(document.value["model"]["width"], 64);
        assert_eq!(document.value["model"]["layers"], 2);

        expect_ok(fs::remove_dir_all(root).map_err(|error| {
            RlabError::config(format!("failed to clean temporary config dir: {error}"))
        }));
    }

    #[test]
    fn rejects_cycles() {
        let root = temp_dir();

        expect_ok(
            fs::write(root.join("a.yaml"), "extends: b\n")
                .map_err(|error| RlabError::config(format!("failed to write config a: {error}"))),
        );

        expect_ok(
            fs::write(root.join("b.yaml"), "extends: a\n")
                .map_err(|error| RlabError::config(format!("failed to write config b: {error}"))),
        );

        assert!(resolve_document(&root, "a", ".yaml", BTreeMap::new(), true).is_err());

        expect_ok(fs::remove_dir_all(root).map_err(|error| {
            RlabError::config(format!("failed to clean temporary config dir: {error}"))
        }));
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected Ok(..), got Err({error})"),
        }
    }
}
