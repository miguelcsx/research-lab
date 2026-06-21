use std::collections::BTreeMap;
use std::io::IsTerminal;

use rlab_core::diagnostic::{DiagnosticFinding, DiagnosticLevel};
use rlab_core::registry::Registry;
use rlab_core::run::RunSummary;
use rlab_core::RlabResult;

pub fn print_line(value: &str) {
    println!("{value}");
}

pub fn print_registry(registry: &Registry) -> RlabResult<()> {
    print_line(&format!(
        "{}  {}",
        accent("rlab discover"),
        dim(&registry_summary(registry))
    ));
    print_registry_group(registry, "Runnable", |kind| kind.is_runnable())?;
    print_registry_group(registry, "Support", |kind| kind.is_support())?;
    print_registry_group(registry, "Internal", |kind| kind.is_internal())?;
    print_registry_group(registry, "Custom", |kind| {
        !kind.is_runnable() && !kind.is_support() && !kind.is_internal()
    })?;
    Ok(())
}

fn print_registry_group(
    registry: &Registry,
    label: &str,
    include: impl Fn(&rlab_core::RegistryKind) -> bool,
) -> RlabResult<()> {
    let records = registry
        .records
        .iter()
        .filter(|record| include(&record.kind))
        .collect::<Vec<_>>();
    if records.is_empty() {
        return Ok(());
    }
    print_line("");
    print_line(&format!(
        "{} {}",
        section(label),
        dim(&format!("{} entries", records.len()))
    ));

    let mut by_kind: BTreeMap<&str, Vec<&rlab_core::registry::RegistryRecord>> = BTreeMap::new();
    for record in records {
        by_kind
            .entry(record.kind.as_str())
            .or_default()
            .push(record);
    }
    for (kind, records) in by_kind {
        print_line(&format!(
            "  {} {}",
            kind_badge(kind),
            dim(&format!("{} entries", records.len()))
        ));
        for record in records {
            print_line(&format!("    {}", target(&registry_reference(record))));
            print_line(&format!(
                "      {} {}",
                dim("source"),
                path(&record.source.display().to_string())
            ));
            if record.version != "1" || !record.tags.is_empty() {
                print_line(&format!("      {}", dim(&registry_details(record))));
            }
        }
    }
    Ok(())
}

fn registry_summary(registry: &Registry) -> String {
    let mut counts: BTreeMap<&str, usize> = BTreeMap::new();
    for record in &registry.records {
        *counts.entry(record.kind.as_str()).or_default() += 1;
    }
    let details = counts
        .into_iter()
        .map(|(kind, count)| format!("{kind}={count}"))
        .collect::<Vec<_>>()
        .join(", ");
    format!("registry: {} records ({details})", registry.records.len())
}

fn registry_reference(record: &rlab_core::registry::RegistryRecord) -> String {
    format!("{}:{}", record.kind.as_str(), record.name)
}

fn registry_details(record: &rlab_core::registry::RegistryRecord) -> String {
    let mut details = vec![format!("version {}", record.version)];
    if !record.tags.is_empty() {
        details.push(format!("tags {}", record.tags.join(",")));
    }
    details.join("  ")
}

pub fn print_runs(runs: &[RunSummary]) -> RlabResult<()> {
    print_line(&format!(
        "{}  {}",
        accent("rlab runs"),
        dim(&format!("{} runs", runs.len()))
    ));
    for run in runs {
        print_line(&format!(
            "  {}  {}",
            status(run.status.as_str()),
            target(&run.id)
        ));
        print_line(&format!(
            "      {} {}:{}",
            dim("target"),
            kind_badge(&run.operation),
            run.name
        ));
    }
    Ok(())
}

pub fn print_findings(findings: &[DiagnosticFinding]) {
    if findings.is_empty() {
        print_line(&format!("{} {}", accent("doctor"), success("no findings")));
        return;
    }
    for finding in findings {
        let level = match &finding.level {
            DiagnosticLevel::Info => "info",
            DiagnosticLevel::Warning => "warning",
            DiagnosticLevel::Error => "error",
        };
        print_line(&format!("{} {}", status(level), finding.message));
    }
}

pub fn accent(value: &str) -> String {
    paint(value, "1;36")
}

pub fn section(value: &str) -> String {
    paint(value, "1;35")
}

pub fn target(value: &str) -> String {
    paint(value, "1;37")
}

pub fn path(value: &str) -> String {
    paint(value, "36")
}

pub fn dim(value: &str) -> String {
    paint(value, "2")
}

pub fn success(value: &str) -> String {
    paint(value, "32")
}

pub fn warn(value: &str) -> String {
    paint(value, "33")
}

pub fn error(value: &str) -> String {
    paint(value, "31")
}

pub fn kind_badge(kind: &str) -> String {
    let color = match kind {
        "experiment" | "study" => "35",
        "workflow" => "34",
        "benchmark" => "33",
        "evaluation" => "32",
        "adapter" | "loader" | "executor" | "resolver" | "exporter" | "reporter" | "notifier" => {
            "36"
        }
        _ => "37",
    };
    paint(kind, color)
}

pub fn status(value: &str) -> String {
    match value {
        "completed" | "ok" | "info" => success(value),
        "running" => paint(value, "34"),
        "failed" | "error" => error(value),
        "cancelled" | "warn" | "warning" => warn(value),
        _ => paint(value, "37"),
    }
}

fn paint(value: &str, code: &str) -> String {
    if color_enabled() {
        format!("\x1b[{code}m{value}\x1b[0m")
    } else {
        value.to_string()
    }
}

fn color_enabled() -> bool {
    match std::env::var("RLAB_COLOR").ok().as_deref() {
        Some("always" | "1" | "true") => return true,
        Some("never" | "0" | "false") => return false,
        _ => {}
    }
    if std::env::var_os("NO_COLOR").is_some() {
        return false;
    }
    if std::env::var("TERM").ok().as_deref() == Some("dumb") {
        return false;
    }
    std::io::stdout().is_terminal()
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::path::PathBuf;

    use super::{registry_reference, registry_summary};
    use rlab_core::{Registry, RegistryKind, RegistryRecord, RegistryRecordSpec};

    fn record(kind: RegistryKind, name: &str) -> RegistryRecord {
        RegistryRecord::from_spec(RegistryRecordSpec {
            kind,
            name: name.to_string(),
            version: "1".to_string(),
            module: "project.module".to_string(),
            qualname: name.to_string(),
            source: PathBuf::from("project/module.py"),
            tags: Vec::new(),
            description: String::new(),
            metadata: BTreeMap::new(),
        })
    }

    #[test]
    fn renders_standard_registry_reference() {
        assert_eq!(
            registry_reference(&record(RegistryKind::EXPERIMENT, "project.clean")),
            "experiment:project.clean"
        );
    }

    #[test]
    fn renders_namespaced_component_reference() {
        assert_eq!(
            registry_reference(&record(
                RegistryKind::parse("tokenizer").expect("custom kind"),
                "bpe"
            )),
            "tokenizer:bpe"
        );
    }

    #[test]
    fn renders_registry_summary_counts_by_kind() {
        let mut registry = Registry::new();
        registry
            .insert(record(RegistryKind::EXPERIMENT, "project.clean"))
            .expect("insert");
        registry
            .insert(record(
                RegistryKind::parse("tokenizer").expect("kind"),
                "bpe",
            ))
            .expect("insert");

        assert_eq!(
            registry_summary(&registry),
            "registry: 2 records (experiment=1, tokenizer=1)"
        );
    }
}
