use rlab_core::diagnostic::{DiagnosticFinding, DiagnosticLevel};
use rlab_core::output::Table;
use rlab_core::registry::Registry;
use rlab_core::run::RunSummary;
use rlab_core::RlabResult;

pub fn print_line(value: &str) {
    println!("{value}");
}

pub fn print_registry(registry: &Registry) -> RlabResult<()> {
    let mut table = Table::new(vec![
        "kind".to_string(),
        "ref".to_string(),
        "version".to_string(),
        "source".to_string(),
    ])?;
    for record in &registry.records {
        table.push_row(vec![
            record.kind.as_str().to_string(),
            registry_reference(record),
            record.version.clone(),
            record.source.display().to_string(),
        ])?;
    }
    print_line(&table.render_plain());
    Ok(())
}

fn registry_reference(record: &rlab_core::registry::RegistryRecord) -> String {
    if record.kind == rlab_core::registry::RegistryKind::Component {
        if let Some(component_kind) = record
            .metadata
            .get("component_kind")
            .and_then(serde_json::Value::as_str)
        {
            return format!("{component_kind}:{}", record.name);
        }
    }
    format!("{}:{}", record.kind.as_str(), record.name)
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;
    use std::path::PathBuf;

    use rlab_core::{RegistryKind, RegistryRecord};
    use serde_json::json;

    use super::registry_reference;

    fn record(kind: RegistryKind, name: &str) -> RegistryRecord {
        RegistryRecord::new(
            kind,
            name.to_string(),
            "1".to_string(),
            "project.module".to_string(),
            name.to_string(),
            PathBuf::from("project/module.py"),
            Vec::new(),
            String::new(),
            BTreeMap::new(),
        )
    }

    #[test]
    fn renders_standard_registry_reference() {
        assert_eq!(
            registry_reference(&record(RegistryKind::Dataset, "project.clean")),
            "dataset:project.clean"
        );
    }

    #[test]
    fn renders_component_reference_using_component_kind() {
        let mut record = record(RegistryKind::Component, "bpe");
        record
            .metadata
            .insert("component_kind".to_string(), json!("tokenizer"));

        assert_eq!(registry_reference(&record), "tokenizer:bpe");
    }
}

pub fn print_runs(runs: &[RunSummary]) -> RlabResult<()> {
    let mut table = Table::new(vec![
        "id".to_string(),
        "operation".to_string(),
        "name".to_string(),
        "status".to_string(),
    ])?;
    for run in runs {
        table.push_row(vec![
            run.id.clone(),
            run.operation.clone(),
            run.name.clone(),
            run.status.as_str().to_string(),
        ])?;
    }
    print_line(&table.render_plain());
    Ok(())
}

pub fn print_findings(findings: &[DiagnosticFinding]) {
    if findings.is_empty() {
        print_line("doctor: no findings");
        return;
    }
    for finding in findings {
        let level = match &finding.level {
            DiagnosticLevel::Info => "info",
            DiagnosticLevel::Warning => "warning",
            DiagnosticLevel::Error => "error",
        };
        print_line(&format!("{level}: {}", finding.message));
    }
}
