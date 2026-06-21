use std::path::{Path, PathBuf};
use std::process::Command;

use clap::Args;
use rlab_core::{
    config::ProjectPaths,
    load_effective_config,
    registry::{hash_strings, load_registry_cache, save_registry_cache, RegistryCacheKey},
    Registry, RlabResult,
};

use crate::host::execution;
use crate::render::{
    human::{print_line, print_registry},
    json::print_json,
};

#[derive(Debug, Args)]
pub struct DiscoverCommand {
    /// Show only records of this registry kind, for example `experiment`.
    pub kind: Option<String>,
    #[arg(long)]
    pub refresh: bool,
    #[arg(long)]
    pub no_cache: bool,
    #[arg(long)]
    pub strict: bool,
    #[arg(long)]
    pub all: bool,
}

pub fn run(command: DiscoverCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;
    let strict = command.strict || config.production.strict;
    let registry = discover_registry(&config, &paths, strict, command.refresh || command.no_cache)?;
    render(
        filter_registry(registry, command.kind.as_deref(), command.all)?,
        json,
    )?;
    Ok(0)
}

pub fn discover_registry(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    strict: bool,
    refresh: bool,
) -> RlabResult<Registry> {
    let cache_key = cache_key_for(config, strict)?;
    if !refresh {
        if let Some(registry) = load_registry_cache(&paths.registry_cache, &cache_key)? {
            return Ok(registry);
        }
    }
    let registry = execution::discover_registry(config, strict)?;
    save_registry_cache(&paths.registry_cache, registry.clone(), &cache_key)?;
    Ok(registry)
}

fn filter_registry(mut registry: Registry, kind: Option<&str>, all: bool) -> RlabResult<Registry> {
    let Some(kind) = kind else {
        if !all {
            registry
                .records
                .retain(|record| record.kind.is_runtime_visible());
        }
        return Ok(registry);
    };
    if normalize_kind(kind) == "support" {
        registry.records.retain(|record| record.kind.is_support());
        return Ok(registry);
    }
    let kind = rlab_core::RegistryKind::parse(normalize_kind(kind))?;
    registry.records.retain(|record| record.kind == kind);
    Ok(registry)
}

fn normalize_kind(kind: &str) -> &str {
    match kind {
        "studies" => "study",
        _ => kind.strip_suffix('s').unwrap_or(kind),
    }
}

fn render(registry: Registry, json: bool) -> RlabResult<()> {
    if json {
        print_json("discover", registry)
    } else if registry.records.is_empty() {
        print_line("no registry records discovered");
        Ok(())
    } else {
        print_registry(&registry)
    }
}

pub fn cache_key_for(
    config: &rlab_core::EffectiveConfig,
    strict: bool,
) -> RlabResult<RegistryCacheKey> {
    let config_hash =
        hash_strings(
            &[serde_json::to_string(config).map_err(rlab_core::RlabError::serialization)?],
        );
    Ok(RegistryCacheKey {
        rlab_version: env!("CARGO_PKG_VERSION").to_string(),
        config_hash,
        modules: config.python.modules.clone(),
        source_paths: infer_source_paths(&config.project.root, &config.python.modules),
        python_executable: config.python.executable.clone(),
        python_version: detect_python_version(&config.project.root, &config.python.executable),
        strict_policy_hash: hash_strings(&[strict.to_string()]),
    })
}

fn detect_python_version(root: &Path, executable: &str) -> String {
    let executable = {
        let path = PathBuf::from(executable);
        if path.is_absolute() {
            path
        } else {
            root.join(path)
        }
    };
    Command::new(executable)
        .arg("--version")
        .output()
        .ok()
        .and_then(|output| {
            String::from_utf8(output.stdout)
                .ok()
                .filter(|s| !s.trim().is_empty())
                .or_else(|| String::from_utf8(output.stderr).ok())
        })
        .map(|s| s.trim().to_string())
        .unwrap_or_else(|| "unknown".to_string())
}

fn infer_source_paths(root: &Path, modules: &[String]) -> Vec<PathBuf> {
    let mut paths: Vec<PathBuf> = modules
        .iter()
        .flat_map(|module| module_candidates(root, module))
        .filter(|path| path.exists())
        .collect();
    collect_declaration_documents(&root.join("configs"), &mut paths);
    paths
}

fn module_candidates(root: &Path, module: &str) -> Vec<PathBuf> {
    let rel = module.replace('.', std::path::MAIN_SEPARATOR_STR);
    let module_file = root.join(format!("{rel}.py"));
    let package = root.join(&rel);
    let mut paths = vec![module_file];
    collect_python_sources(&package, &mut paths);
    paths
}

fn collect_python_sources(directory: &Path, paths: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(directory) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_python_sources(&path, paths);
        } else if path.extension().is_some_and(|extension| extension == "py") {
            paths.push(path);
        }
    }
}

fn collect_declaration_documents(directory: &Path, paths: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(directory) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_dir() {
            collect_declaration_documents(&path, paths);
        } else if path.extension().is_some_and(is_declaration_extension) {
            paths.push(path);
        }
    }
}

fn is_declaration_extension(extension: &std::ffi::OsStr) -> bool {
    matches!(extension.to_str(), Some("json" | "toml" | "yaml" | "yml"))
}

#[cfg(test)]
mod tests {
    use std::fs;

    use rlab_core::{Registry, RegistryKind, RegistryRecord, RegistryRecordSpec};

    use super::{filter_registry, infer_source_paths, module_candidates};

    fn registry() -> Registry {
        let mut registry = Registry::new();
        for (kind, name) in [
            (RegistryKind::EXPERIMENT, "train"),
            (RegistryKind::LOADER, "artifact"),
            (
                RegistryKind::parse("tokenizer").expect("custom kind"),
                "bpe",
            ),
        ] {
            registry
                .insert(RegistryRecord::from_spec(RegistryRecordSpec {
                    kind,
                    name: name.to_string(),
                    version: "1".to_string(),
                    module: "project".to_string(),
                    qualname: name.to_string(),
                    source: "project.py".into(),
                    tags: Vec::new(),
                    description: String::new(),
                    metadata: Default::default(),
                }))
                .expect("valid registry record");
        }
        registry
    }

    #[test]
    fn filters_by_singular_kind() {
        let filtered = filter_registry(registry(), Some("experiment"), false).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::EXPERIMENT);
    }

    #[test]
    fn filters_by_support_pseudo_kind() {
        let filtered = filter_registry(registry(), Some("support"), false).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::LOADER);
    }

    #[test]
    fn filters_studies_by_plural_kind() {
        let mut registry = registry();
        registry
            .insert(RegistryRecord::from_spec(RegistryRecordSpec {
                kind: RegistryKind::STUDY,
                name: "comparison".to_string(),
                version: "1".to_string(),
                module: "project".to_string(),
                qualname: "comparison".to_string(),
                source: "project.py".into(),
                tags: Vec::new(),
                description: String::new(),
                metadata: Default::default(),
            }))
            .expect("valid registry record");

        let filtered = filter_registry(registry, Some("studies"), false).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::STUDY);
    }

    #[test]
    fn default_filter_hides_custom_records() {
        let filtered = filter_registry(registry(), None, false).expect("valid filter");
        assert_eq!(filtered.records.len(), 2);
        assert!(filtered
            .records
            .iter()
            .all(|record| record.kind.is_runtime_visible()));
    }

    #[test]
    fn all_filter_keeps_custom_records() {
        let filtered = filter_registry(registry(), None, true).expect("valid filter");
        assert_eq!(filtered.records.len(), 3);
    }

    #[test]
    fn package_cache_key_includes_nested_python_sources() {
        let root =
            std::env::temp_dir().join(format!("rlab-discovery-sources-{}", std::process::id()));
        let package = root.join("training").join("experiments");
        fs::create_dir_all(package.join("nested")).expect("create package");
        fs::write(package.join("__init__.py"), "").expect("write init");
        fs::write(package.join("catalog.py"), "").expect("write module");
        fs::write(package.join("nested").join("component.py"), "").expect("write nested module");

        let paths = module_candidates(&root, "training.experiments");

        assert!(paths.contains(&package.join("__init__.py")));
        assert!(paths.contains(&package.join("catalog.py")));
        assert!(paths.contains(&package.join("nested").join("component.py")));
        fs::remove_dir_all(root).expect("remove package");
    }

    #[test]
    fn cache_key_includes_declarative_config_documents() {
        let root =
            std::env::temp_dir().join(format!("rlab-discovery-configs-{}", std::process::id()));
        let configs = root.join("configs").join("experiments");
        fs::create_dir_all(&configs).expect("create configs");
        fs::write(configs.join("baseline.yaml"), "model: {}\n").expect("write config");

        let paths = infer_source_paths(&root, &[]);

        assert!(paths.contains(&configs.join("baseline.yaml")));
        fs::remove_dir_all(root).expect("remove configs");
    }
}
