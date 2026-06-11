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
    let cache_key = cache_key_for(&config, strict)?;
    if !command.refresh && !command.no_cache {
        if let Some(registry) = load_registry_cache(&paths.registry_cache, &cache_key)? {
            render(registry, json)?;
            return Ok(0);
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
    render(registry, json)?;
    Ok(0)
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

fn cache_key_for(
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
    vec![
        root.join(format!("{rel}.py")),
        root.join(&rel).join("__init__.py"),
    ]
}
