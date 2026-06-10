use super::finding::DiagnosticFinding;

pub fn render_findings(findings: &[DiagnosticFinding]) -> Vec<String> {
    findings
        .iter()
        .map(|finding| format!("{:?}: {} ({})", finding.level, finding.message, finding.code))
        .collect()
}
