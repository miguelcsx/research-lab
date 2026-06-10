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
        "name".to_string(),
        "version".to_string(),
        "source".to_string(),
    ])?;
    for record in &registry.records {
        table.push_row(vec![
            record.kind.as_str().to_string(),
            record.name.clone(),
            record.version.clone(),
            record.source.display().to_string(),
        ])?;
    }
    print_line(&table.render_plain());
    Ok(())
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
