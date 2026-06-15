use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde_json::Value;

use crate::error::RlabResult;
use crate::fs::write_text_atomic;

pub fn write_markdown_report(
    path: &Path,
    title: &str,
    fields: &BTreeMap<String, Value>,
) -> RlabResult<PathBuf> {
    write_text_atomic(path, &markdown_report(title, fields))?;
    Ok(path.to_path_buf())
}

pub fn write_markdown_card(
    path: &Path,
    title: &str,
    sections: &BTreeMap<String, BTreeMap<String, Value>>,
) -> RlabResult<PathBuf> {
    write_text_atomic(path, &markdown_card(title, sections))?;
    Ok(path.to_path_buf())
}

fn markdown_report(title: &str, fields: &BTreeMap<String, Value>) -> String {
    let mut lines = vec![format!("# {}", inline(title)), String::new()];
    push_fields(&mut lines, fields);
    document(lines)
}

fn markdown_card(title: &str, sections: &BTreeMap<String, BTreeMap<String, Value>>) -> String {
    let mut lines = vec![format!("# {}", inline(title)), String::new()];
    for (section, fields) in sections {
        lines.push(format!("## {}", inline(section)));
        lines.push(String::new());
        push_fields(&mut lines, fields);
        lines.push(String::new());
    }
    document(lines)
}

fn push_fields(lines: &mut Vec<String>, fields: &BTreeMap<String, Value>) {
    lines.extend(
        fields
            .iter()
            .map(|(key, value)| format!("- **{}**: {}", inline(key), inline_value(value))),
    );
}

fn document(lines: Vec<String>) -> String {
    format!("{}\n", lines.join("\n").trim_end())
}

fn inline_value(value: &Value) -> String {
    match value {
        Value::Null => "null".to_string(),
        Value::String(text) => inline(text),
        other => inline(&other.to_string()),
    }
}

fn inline(value: &str) -> String {
    value
        .replace('\n', " ")
        .chars()
        .flat_map(|char| {
            if "\\`*_{}[]()#+-.!|>".contains(char) {
                vec!['\\', char]
            } else {
                vec![char]
            }
        })
        .collect()
}
