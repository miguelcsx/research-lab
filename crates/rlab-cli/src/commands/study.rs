use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, search_project, HostCommand,
    HostRequest, HostTarget, ProtocolVersion, RegistryKind, RlabResult, RunSession,
};

use crate::commands::run::process_event_public;
use crate::host::process::run_python_host;
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct StudyCommand {
    #[command(subcommand)]
    pub command: StudySubcommand,
}

#[derive(Debug, Subcommand)]
pub enum StudySubcommand {
    List,
    Show {
        name: String,
    },
    Run {
        name: String,
        #[arg(long)]
        strict: bool,
    },
}

pub fn run(command: StudyCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        StudySubcommand::List => {
            let hits = search_project(&paths, "study", Some("registry"))?;
            if json {
                print_json("study_list", hits)?;
            } else {
                for hit in hits {
                    print_line(&hit.id);
                }
            }
            Ok(0)
        }
        StudySubcommand::Show { name } => {
            let hits = search_project(&paths, &name, None)?;
            if json {
                print_json("study_show", hits)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&hits)
                        .map_err(rlab_core::RlabError::serialization)?,
                );
            }
            Ok(0)
        }
        StudySubcommand::Run { name, strict } => run_study(&config, &paths, name, strict, json),
    }
}

fn run_study(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    name: String,
    strict: bool,
    json: bool,
) -> RlabResult<u8> {
    let params = serde_json::json!({});
    let session = RunSession::create(
        paths,
        RegistryKind::Study.as_str(),
        &name,
        std::env::args().collect(),
        params.clone(),
    )?;
    let request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: session.directory.id.as_str().to_string(),
        command: HostCommand::Execute,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: Some(HostTarget {
            kind: RegistryKind::Study,
            name,
        }),
        run_id: Some(session.directory.id.as_str().to_string()),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
        params,
        seed: None,
        strict: strict || config.production.strict,
        environment: serde_json::json!({}),
    };
    let events = run_python_host(
        &config.python.executable,
        &config.python.runner_module,
        &request,
    )?;
    let mut completed = None;
    let mut failed = None;
    for event in &events {
        validate_event(event)?;
        process_event_public(&session, event, &mut completed, &mut failed)?;
    }
    if let Some(error) = failed {
        let run = session.fail(&error.to_string())?;
        if json {
            print_json("study_run", run)?;
        } else {
            print_line(&format!("study failed: {}", run.id.as_str()));
        }
        return Ok(1);
    }
    let result = match completed {
        Some(value) => value,
        None => serde_json::json!({"schema_version": SCHEMA_VERSION,"data":{}}),
    };
    let run = session.complete(result)?;
    if json {
        print_json("study_run", run)?;
    } else {
        print_line(&format!("completed study run: {}", run.id.as_str()));
    }
    Ok(0)
}
