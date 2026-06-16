use std::path::Path;

use clap::Args;
use rlab_core::{
    config::ProjectPaths, load_effective_config, RegistryKind, RegistryRecord, RlabError,
    RlabResult,
};

use crate::commands::discover::discover_registry;
use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct ExplainCommand {
    /// Registry reference to inspect, for example `experiment:babylm.smoke`.
    pub reference: String,
    #[arg(long)]
    pub refresh: bool,
    #[arg(long)]
    pub strict: bool,
}

pub fn run(command: ExplainCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    paths.ensure_base_dirs()?;
    let (kind, name) = parse_reference(&command.reference)?;
    let strict = command.strict || config.production.strict;
    let registry = discover_registry(&config, &paths, strict, command.refresh)?;
    let Some(record) = registry
        .records
        .iter()
        .find(|record| record.kind == kind && record.name == name)
    else {
        let suggestion = nearest_ref(&registry.records, &kind, name)
            .map(|value| format!(" Did you mean `{value}`?"))
            .unwrap_or_default();
        return Err(RlabError::Reference {
            message: format!(
                "unknown registry ref '{}'.{} Run `rlab discover {} --refresh` to inspect available records.",
                command.reference,
                suggestion,
                kind.as_str()
            ),
        });
    };
    if json {
        print_json("explain", record)?;
    } else {
        print_line(&format!("ref: {}:{}", record.kind.as_str(), record.name));
        print_line(&format!("source: {}", record.source.display()));
        if !record.description.is_empty() {
            print_line(&format!("description: {}", record.description));
        }
        if !record.metadata.is_empty() {
            let metadata =
                serde_json::to_string_pretty(&record.metadata).map_err(RlabError::serialization)?;
            print_line("metadata:");
            print_line(&metadata);
        }
    }
    Ok(0)
}

fn parse_reference(reference: &str) -> RlabResult<(RegistryKind, &str)> {
    let Some((kind, name)) = reference.split_once(':') else {
        return Err(RlabError::Reference {
            message: format!("expected <kind>:<name>, got '{reference}'"),
        });
    };
    if name.is_empty() {
        return Err(RlabError::Reference {
            message: format!("missing name in '{reference}'"),
        });
    }
    Ok((RegistryKind::parse(kind)?, name))
}

fn nearest_ref(records: &[RegistryRecord], kind: &RegistryKind, name: &str) -> Option<String> {
    let (best, distance) = records
        .iter()
        .filter(|record| &record.kind == kind)
        .map(|record| (record, edit_distance(&record.name, name)))
        .min_by_key(|(_record, distance)| *distance)?;
    if distance <= usize::max(2, name.len() / 3) {
        Some(format!("{}:{}", best.kind.as_str(), best.name))
    } else {
        None
    }
}

fn edit_distance(left: &str, right: &str) -> usize {
    let mut previous: Vec<usize> = (0..=right.len()).collect();
    for (left_index, left_char) in left.chars().enumerate() {
        let mut current = vec![left_index + 1];
        for (right_index, right_char) in right.chars().enumerate() {
            let insert = current[right_index] + 1;
            let delete = previous[right_index + 1] + 1;
            let replace = previous[right_index] + usize::from(left_char != right_char);
            current.push(insert.min(delete).min(replace));
        }
        previous = current;
    }
    *previous.last().unwrap_or(&0)
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use rlab_core::{RegistryKind, RegistryRecord, RegistryRecordSpec};

    use super::{edit_distance, nearest_ref, parse_reference};

    #[test]
    fn parses_registry_reference() {
        let (kind, name) = parse_reference("experiment:train").expect("valid ref");

        assert_eq!(kind.as_str(), "experiment");
        assert_eq!(name, "train");
    }

    #[test]
    fn rejects_bare_names() {
        assert!(parse_reference("train").is_err());
    }

    #[test]
    fn suggests_nearest_ref_for_same_kind() {
        let kind = RegistryKind::EXPERIMENT;
        let record = RegistryRecord::from_spec(RegistryRecordSpec {
            kind: kind.clone(),
            name: "training.pretrain.clm".to_string(),
            version: "1".to_string(),
            module: "project".to_string(),
            qualname: "clm".to_string(),
            source: PathBuf::from("training.py"),
            tags: Vec::new(),
            description: String::new(),
            metadata: Default::default(),
        });

        assert_eq!(
            nearest_ref(&[record], &kind, "training.pretrain.cl"),
            Some("experiment:training.pretrain.clm".to_string())
        );
    }

    #[test]
    fn computes_edit_distance() {
        assert_eq!(edit_distance("attention", "attenton"), 1);
        assert_eq!(edit_distance("clm", "mlm"), 1);
    }
}
