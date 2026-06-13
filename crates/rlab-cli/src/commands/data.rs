use std::fs;
use std::path::{Path, PathBuf};

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, host::validate_event, load_effective_config, HostCommand, HostRequest,
    HostTarget, ProtocolVersion, RegistryKind, RlabError, RlabResult, RunSession,
};
use serde_json::json;

use crate::commands::run::{parse_params_public, process_event_public};
use crate::host::process::run_python_host;
use crate::render::{human::print_line, json::print_json};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Args)]
pub struct DataCommand {
    #[command(subcommand)]
    pub command: DataSubcommand,
}

#[derive(Debug, Subcommand)]
pub enum DataSubcommand {
    Build {
        dataset: String,
        #[arg(long = "override")]
        overrides: Vec<String>,
        #[arg(long)]
        strict: bool,
    },
    Profile {
        manifest: PathBuf,
    },
    Validate {
        manifest: PathBuf,
    },
    Diff {
        left: PathBuf,
        right: PathBuf,
    },
    Compare {
        left: PathBuf,
        right: PathBuf,
    },
    Sample {
        manifest: PathBuf,
        #[arg(long, default_value_t = 10)]
        n: usize,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    Lineage {
        manifest: PathBuf,
    },
    Audit {
        run_id: String,
    },
    Reasons {
        run_id: String,
    },
    StageSummary {
        run_id: String,
    },
    SourceSummary {
        run_id: String,
    },
    SampleDrops {
        run_id: String,
        reason: String,
    },
    Promote {
        manifest: PathBuf,
        #[arg(long)]
        r#as: String,
        #[arg(long)]
        alias: Option<String>,
    },
}

pub fn run(command: DataCommand, root: Option<&Path>, json_output: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        DataSubcommand::Build {
            dataset,
            overrides,
            strict,
        } => run_data_build(&config, &paths, dataset, overrides, strict, json_output),
        DataSubcommand::Profile { manifest } => render_profile(&manifest, json_output),
        DataSubcommand::Validate { manifest } => validate_manifest(&manifest, json_output),
        DataSubcommand::Lineage { manifest } => render_lineage(&manifest, json_output),
        DataSubcommand::Diff { left, right } => {
            render_diff(&left, &right, json_output, "data_diff")
        }
        DataSubcommand::Compare { left, right } => {
            render_diff(&left, &right, json_output, "data_compare")
        }
        DataSubcommand::Sample {
            manifest,
            n,
            output,
        } => render_sample(&manifest, n, output, json_output),
        DataSubcommand::Audit { run_id } => render_run_file(
            &paths,
            &run_id,
            "artifacts/dataset/audit/summary.json",
            json_output,
            "data_audit",
        ),
        DataSubcommand::Reasons { run_id } => render_run_file(
            &paths,
            &run_id,
            "artifacts/dataset/audit/drop_reasons.csv",
            json_output,
            "data_reasons",
        ),
        DataSubcommand::StageSummary { run_id } => render_run_file(
            &paths,
            &run_id,
            "artifacts/dataset/audit/stage_summary.csv",
            json_output,
            "data_stage_summary",
        ),
        DataSubcommand::SourceSummary { run_id } => render_run_file(
            &paths,
            &run_id,
            "artifacts/dataset/audit/source_summary.csv",
            json_output,
            "data_source_summary",
        ),
        DataSubcommand::SampleDrops { run_id, reason } => {
            render_sample_drops(&paths, &run_id, &reason, json_output)
        }
        DataSubcommand::Promote {
            manifest,
            r#as,
            alias,
        } => promote_manifest(&paths, manifest, r#as, alias, json_output),
    }
}

fn run_data_build(
    config: &rlab_core::EffectiveConfig,
    paths: &ProjectPaths,
    dataset: String,
    overrides: Vec<String>,
    strict: bool,
    json_output: bool,
) -> RlabResult<u8> {
    let name = parse_dataset_name(&dataset)?;
    let params = parse_params_public(&overrides)?;
    let session = RunSession::create(
        paths,
        "data.build",
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
            kind: RegistryKind::DATASET,
            name,
        }),
        run_id: Some(session.directory.id.as_str().to_string()),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(paths.cache.clone()),
        params,
        seed: None,
        strict: strict || config.production.strict,
        environment: json!({}),
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
        if json_output {
            print_json("data_build", run)?;
        } else {
            print_line(&format!("data build failed: {}", run.id.as_str()));
        }
        return Ok(1);
    }
    let result = match completed {
        Some(value) => value,
        None => json!({"schema_version": SCHEMA_VERSION, "data": {"records": 0}}),
    };
    let run = session.complete(result)?;
    if json_output {
        print_json("data_build", run)?;
    } else {
        print_line(&format!("completed data build: {}", run.id.as_str()));
    }
    Ok(0)
}

fn parse_dataset_name(value: &str) -> RlabResult<String> {
    match value.strip_prefix("dataset:") {
        Some(name) if !name.trim().is_empty() => Ok(name.to_string()),
        None if !value.trim().is_empty() => Ok(value.to_string()),
        _ => Err(RlabError::Reference {
            message: format!("invalid dataset reference: {value}"),
        }),
    }
}

fn read_text(path: &Path) -> RlabResult<String> {
    fs::read_to_string(path).map_err(|error| rlab_core::RlabError::io(path, error))
}

fn render_profile(path: &Path, json_output: bool) -> RlabResult<u8> {
    let content = read_text(path)?;
    let lines = content.lines().count();
    let bytes = content.len();
    let first_json = content
        .lines()
        .find(|line| !line.trim().is_empty())
        .and_then(|line| serde_json::from_str::<serde_json::Value>(line).ok());
    let columns = match first_json {
        Some(serde_json::Value::Object(map)) => map.keys().cloned().collect::<Vec<_>>(),
        _ => Vec::new(),
    };
    let result = json!({"schema_version": SCHEMA_VERSION,"path":path.display().to_string(),"records":lines,"bytes":bytes,"columns":columns});
    if json_output {
        print_json("data_profile", result)?;
    } else {
        print_line(&serde_json::to_string_pretty(&result).map_err(RlabError::serialization)?);
    }
    Ok(0)
}

fn validate_manifest(path: &Path, json_output: bool) -> RlabResult<u8> {
    let content = read_text(path)?;
    let parsed = serde_json::from_str::<serde_json::Value>(&content)
        .or_else(|_| {
            let json_str = serde_json::to_string(&content)?;
            serde_json::from_str::<serde_json::Value>(&format!("{{\"text\":{json_str}}}"))
        })
        .map_err(RlabError::serialization)?;
    let has_schema = parsed.get("schema_version").is_some() || content.contains("schema_version");
    let result = json!({"schema_version": SCHEMA_VERSION,"path":path.display().to_string(),"valid":has_schema,"has_schema_version":has_schema});
    if json_output {
        print_json("data_validate", result)?;
    } else {
        print_line(&serde_json::to_string_pretty(&result).map_err(RlabError::serialization)?);
    }
    Ok(if has_schema { 0 } else { 1 })
}

fn render_lineage(path: &Path, json_output: bool) -> RlabResult<u8> {
    let content = read_text(path)?;
    let checksum = rlab_core::artifact::digest::sha256_file(path)?;
    let result = json!({"schema_version": SCHEMA_VERSION,"manifest":path.display().to_string(),"sha256":checksum,"bytes":content.len()});
    if json_output {
        print_json("data_lineage", result)?;
    } else {
        print_line(&serde_json::to_string_pretty(&result).map_err(RlabError::serialization)?);
    }
    Ok(0)
}

fn render_diff(left: &Path, right: &Path, json_output: bool, kind: &str) -> RlabResult<u8> {
    let left_text = read_text(left)?;
    let right_text = read_text(right)?;
    let left_lines = left_text.lines().count();
    let right_lines = right_text.lines().count();
    let result = json!({"schema_version": SCHEMA_VERSION,"left":left.display().to_string(),"right":right.display().to_string(),"same":left_text==right_text,"left_bytes":left_text.len(),"right_bytes":right_text.len(),"left_records":left_lines,"right_records":right_lines,"record_delta":right_lines as i64 - left_lines as i64});
    if json_output {
        print_json(kind, result)?;
    } else {
        print_line(&serde_json::to_string_pretty(&result).map_err(RlabError::serialization)?);
    }
    Ok(0)
}

fn render_sample(
    path: &Path,
    n: usize,
    output: Option<PathBuf>,
    json_output: bool,
) -> RlabResult<u8> {
    let content = read_text(path)?;
    let sample = content.lines().take(n).collect::<Vec<_>>().join("\n");
    if let Some(path) = output {
        rlab_core::fs::write_text_atomic(&path, &sample)?;
        if json_output {
            print_json("data_sample", path.display().to_string())?;
        } else {
            print_line(&format!("wrote {}", path.display()));
        }
    } else if json_output {
        print_json("data_sample", sample)?;
    } else {
        print_line(&sample);
    }
    Ok(0)
}

fn render_sample_drops(
    paths: &ProjectPaths,
    run_id: &str,
    reason: &str,
    json_output: bool,
) -> RlabResult<u8> {
    let path = paths
        .runs
        .join(run_id)
        .join("artifacts/dataset/audit/samples")
        .join(format!("{reason}.jsonl"));
    let text = read_text(&path)?;
    if json_output {
        print_json("data_sample_drops", text)?;
    } else {
        print_line(&text);
    }
    Ok(0)
}

fn promote_manifest(
    paths: &ProjectPaths,
    manifest: PathBuf,
    reference: String,
    alias: Option<String>,
    json_output: bool,
) -> RlabResult<u8> {
    let name = match reference.strip_prefix("dataset:") {
        Some(value) if !value.trim().is_empty() => value.to_string(),
        _ if !reference.trim().is_empty() => reference,
        _ => {
            return Err(RlabError::Reference {
                message: "dataset promotion requires a non-empty reference".to_string(),
            })
        }
    };
    let request = rlab_core::PromoteRequest {
        source: manifest,
        artifact_kind: "dataset".to_string(),
        name,
        version: "1".to_string(),
        alias,
    };
    let promoted = rlab_core::ArtifactStore::new(paths).promote(request)?;
    if json_output {
        print_json("data_promote", promoted)?;
    } else {
        print_line("dataset manifest promoted");
    }
    Ok(0)
}

fn render_run_file(
    paths: &ProjectPaths,
    run_id: &str,
    relative: &str,
    json_output: bool,
    kind: &str,
) -> RlabResult<u8> {
    let path = paths.runs.join(run_id).join(relative);
    let text = read_text(&path)?;
    if json_output {
        print_json(kind, text)?;
    } else {
        print_line(&text);
    }
    Ok(0)
}
