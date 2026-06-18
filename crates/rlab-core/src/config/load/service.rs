use std::path::{Path, PathBuf};

use crate::error::{RlabError, RlabResult};

use super::super::discovery::find_project_root;
use super::super::model::EffectiveConfig;
use super::super::overrides::ConfigOverride;
use super::super::validate::validate_config;

const CURRENT_DIR_ERROR_PATH: &str = ".";

pub fn load_effective_config(
    root: Option<&Path>,
    overrides: &[ConfigOverride],
) -> RlabResult<EffectiveConfig> {
    let project_root = project_root(root)?;
    let project_name = super::infer::infer_project_name(&project_root)?;
    let mut config = EffectiveConfig::default_for(project_root.clone(), project_name);

    super::pyproject::apply_pyproject(&project_root, &mut config)?;
    super::lab_toml::apply_lab_toml(&project_root, &mut config)?;
    super::env::apply_environment(&mut config)?;
    super::overrides::apply_overrides(&mut config, overrides)?;
    super::infer::apply_inferred_modules(&project_root, &mut config);
    validate_config(&config)?;

    Ok(config)
}

fn project_root(root: Option<&Path>) -> RlabResult<PathBuf> {
    match root {
        Some(path) => explicit_project_root(path),
        None => find_project_root(&current_dir()?),
    }
}

fn current_dir() -> RlabResult<PathBuf> {
    std::env::current_dir().map_err(|error| RlabError::io(Path::new(CURRENT_DIR_ERROR_PATH), error))
}

fn explicit_project_root(path: &Path) -> RlabResult<PathBuf> {
    if !path.exists() {
        return Err(RlabError::NotFound {
            subject: format!("project root {}", path.display()),
        });
    }

    path.canonicalize()
        .map_err(|error| RlabError::io(path, error))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    #[test]
    fn explicit_root_is_used_without_project_markers() {
        let root = temp_root("explicit");
        fs::create_dir_all(&root).expect("create temp root");

        let config = expect_ok(load_effective_config(Some(&root), &[]));

        assert_eq!(config.project.root, root.canonicalize().unwrap());
        cleanup(root);
    }

    #[test]
    fn lab_toml_loads_run_defaults() {
        let root = temp_root("run-defaults");
        fs::create_dir_all(&root).expect("create temp root");
        fs::write(
            root.join("lab.toml"),
            r#"
[project]
name = "demo"

[run]
default_seed = 42

[run.params]
device = "auto"

[run.env]
PYTORCH_ENABLE_MPS_FALLBACK = "0"
"#,
        )
        .expect("write lab.toml");

        let config = expect_ok(load_effective_config(Some(&root), &[]));

        assert_eq!(config.run.default_seed, Some(42));
        assert_eq!(
            config.run.params.get("device"),
            Some(&serde_json::json!("auto"))
        );
        assert_eq!(
            config.run.env.get("PYTORCH_ENABLE_MPS_FALLBACK"),
            Some(&"0".to_owned())
        );
        cleanup(root);
    }

    fn temp_root(label: &str) -> PathBuf {
        let unique = match SystemTime::now().duration_since(UNIX_EPOCH) {
            Ok(duration) => duration.as_nanos(),
            Err(_) => 0,
        };
        std::env::temp_dir().join(format!("rlab-config-root-{label}-{unique}"))
    }

    fn cleanup(root: PathBuf) {
        if root.exists() {
            fs::remove_dir_all(root).expect("remove temp root");
        }
    }

    fn expect_ok<T>(result: RlabResult<T>) -> T {
        match result {
            Ok(value) => value,
            Err(error) => panic!("expected ok, got {error}"),
        }
    }
}
