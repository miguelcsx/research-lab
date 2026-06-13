use std::path::{Path, PathBuf};
use std::process::Command;

use clap::Args;
use rlab_core::{
    config::ProjectPaths,
    host::validate_event,
    load_effective_config,
    registry::{hash_strings, load_registry_cache, save_registry_cache, RegistryCacheKey},
    HostCommand, HostEvent, HostRequest, ProtocolVersion, Registry, RlabResult,
};

use crate::host::process::run_python_host;
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
}

pub fn run(command: DiscoverCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;
    let strict = command.strict || config.production.strict;
    let registry = discover_registry(&config, &paths, strict, command.refresh || command.no_cache)?;
    render(filter_registry(registry, command.kind.as_deref())?, json)?;
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
    let request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: "discover".to_string(),
        command: HostCommand::Discover,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: None,
        run_id: None,
        run_dir: None,
        cache_dir: None,
        params: serde_json::json!({}),
        seed: None,
        strict,
        environment: serde_json::json!({
            "python_executable": config.python.executable,
            "runner_module": config.python.runner_module,
        }),
    };
    let events = run_python_host(
        &config.python.executable,
        &config.python.runner_module,
        &request,
    )?;
    let mut registry = Registry::new();
    for event in &events {
        validate_event(event)?;
        collect_registry_event(event, &mut registry)?;
    }
    save_registry_cache(&paths.registry_cache, registry.clone(), &cache_key)?;
    Ok(registry)
}

fn filter_registry(mut registry: Registry, kind: Option<&str>) -> RlabResult<Registry> {
    let Some(kind) = kind else {
        return Ok(registry);
    };
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

fn collect_registry_event(event: &HostEvent, registry: &mut Registry) -> RlabResult<()> {
    match event {
        HostEvent::RegistryRecord(record) => registry.insert(record.record.clone()),
        HostEvent::Failed { error, .. } => Err(rlab_core::RlabError::Host {
            message: error.to_string(),
        }),
        HostEvent::Batch { events, .. } => {
            for nested in events {
                collect_registry_event(nested, registry)?;
            }
            Ok(())
        }
        _ => Ok(()),
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
        python_version: detect_python_version(&config.python.executable),
        strict_policy_hash: hash_strings(&[strict.to_string()]),
    })
}

fn detect_python_version(executable: &str) -> String {
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
    modules
        .iter()
        .flat_map(|module| module_candidates(root, module))
        .filter(|path| path.exists())
        .collect()
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

#[cfg(test)]
mod tests {
    use std::fs;

    use rlab_core::{Registry, RegistryKind, RegistryRecord, RegistryRecordSpec};

    use super::{filter_registry, module_candidates};

    fn registry() -> Registry {
        let mut registry = Registry::new();
        for (kind, name) in [
            (RegistryKind::EXPERIMENT, "train"),
            (RegistryKind::DATASET, "corpus"),
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
        let filtered = filter_registry(registry(), Some("experiment")).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::EXPERIMENT);
    }

    #[test]
    fn filters_by_plural_kind() {
        let filtered = filter_registry(registry(), Some("datasets")).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::DATASET);
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

        let filtered = filter_registry(registry, Some("studies")).expect("valid kind");
        assert_eq!(filtered.records.len(), 1);
        assert_eq!(filtered.records[0].kind, RegistryKind::STUDY);
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
}
