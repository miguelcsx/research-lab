use std::path::{Path, PathBuf};

use clap::{Args, Subcommand};
use rlab_core::{
    artifact::describe_artifact, config::ProjectPaths, load_effective_config, ArtifactStore,
    PromoteRequest, RlabError, RlabResult,
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
            let (kind, name, version) = parse_artifact_reference(&reference)?;
            let manifest = describe_artifact(&paths, &kind, &name, &version)?;
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

fn parse_artifact_name(value: &str) -> RlabResult<(String, String)> {
    let mut split = value.splitn(2, ':');
    let kind = match split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact name: {value}"),
            })
        }
    };
    let name = match split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("artifact reference must be kind:name: {value}"),
            })
        }
    };
    Ok((kind, name))
}

fn parse_artifact_reference(value: &str) -> RlabResult<(String, String, String)> {
    let without_scheme = match value.strip_prefix("artifact:") {
        Some(text) => text,
        None => value,
    };
    let mut version_split = without_scheme.splitn(2, '@');
    let left = match version_split.next() {
        Some(text) if !text.trim().is_empty() => text,
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact reference: {value}"),
            })
        }
    };
    let version = match version_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => "1".to_string(),
    };
    let mut kind_split = left.splitn(2, '/');
    let kind = match kind_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("invalid artifact reference: {value}"),
            })
        }
    };
    let name = match kind_split.next() {
        Some(text) if !text.trim().is_empty() => text.to_string(),
        _ => {
            return Err(RlabError::Reference {
                message: format!("artifact reference must be artifact:kind/name@version: {value}"),
            })
        }
    };
    Ok((kind, name, version))
}
