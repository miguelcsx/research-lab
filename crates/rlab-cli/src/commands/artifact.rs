use std::path::{Path, PathBuf};

use clap::{Args, Subcommand};
use rlab_core::{
    artifact::{describe_artifact_reference, parse_artifact_name},
    config::ProjectPaths,
    load_effective_config, ArtifactStore, PromoteRequest, RlabError, RlabResult,
};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ArtifactCommand {
    #[command(subcommand)]
    pub command: ArtifactSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum ArtifactSubcommand {
    Promote {
        path: PathBuf,
        #[arg(long)]
        r#as: String,
        #[arg(long)]
        version: String,
        #[arg(long)]
        alias: Option<String>,
    },
    Describe {
        reference: String,
    },
}

pub fn run(command: ArtifactCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        ArtifactSubcommand::Promote {
            path,
            r#as,
            version,
            alias,
        } => {
            let (kind, name) = parse_artifact_name(&r#as)?;
            let manifest = ArtifactStore::new(&paths).promote(PromoteRequest {
                source: path,
                artifact_kind: kind,
                name,
                version,
                alias,
            })?;
            if json {
                print_json("artifact_promote", manifest)?;
            } else {
                print_line(&format!(
                    "promoted artifact: {}/{}@{}",
                    manifest.reference.kind, manifest.reference.name, manifest.reference.version
                ));
            }
        }
        ArtifactSubcommand::Describe { reference } => {
            let manifest = describe_artifact_reference(&paths, &reference)?;
            if json {
                print_json("artifact_describe", manifest)?;
            } else {
                print_line(
                    &serde_json::to_string_pretty(&manifest).map_err(RlabError::serialization)?,
                );
            }
        }
    }
    Ok(0)
}
