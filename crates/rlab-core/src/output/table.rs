use crate::error::{RlabError, RlabResult};

#[derive(Debug, Clone)]
pub struct Table {
    headers: Vec<String>,
    rows: Vec<Vec<String>>,
}

impl Table {
    pub fn new(headers: Vec<String>) -> RlabResult<Self> {
        if headers.is_empty() {
            return Err(RlabError::Validation {
                message: "table requires at least one header".to_string(),
            });
        }
        if headers.iter().any(|header| header.trim().is_empty()) {
            return Err(RlabError::Validation {
                message: "table headers cannot be empty".to_string(),
            });
        }
        Ok(Self {
            headers,
            rows: Vec::new(),
        })
    }

    pub fn push_row(&mut self, row: Vec<String>) -> RlabResult<()> {
        if row.len() != self.headers.len() {
            return Err(RlabError::Validation {
                message: format!(
                    "table row has {} cells but expected {}",
                    row.len(),
                    self.headers.len()
                ),
            });
        }
        self.rows.push(row);
        Ok(())
    }

    pub fn render_plain(&self) -> String {
        let widths = self.column_widths();
        let mut output = String::new();
        render_row(&mut output, &self.headers, &widths);
        render_separator(&mut output, &widths);
        for row in &self.rows {
            render_row(&mut output, row, &widths);
        }
        output
    }

    pub fn render_tsv(&self) -> String {
        render_rows(
            &self.headers.iter().map(String::as_str).collect::<Vec<_>>(),
            &self.rows,
        )
    }

    fn column_widths(&self) -> Vec<usize> {
        let mut widths = self
            .headers
            .iter()
            .map(|value| value.chars().count())
            .collect::<Vec<_>>();
        for row in &self.rows {
            for (index, cell) in row.iter().enumerate() {
                let width = cell.chars().count();
                if let Some(current) = widths.get_mut(index) {
                    if width > *current {
                        *current = width;
                    }
                }
            }
        }
        widths
    }
}

pub fn render_rows(headers: &[&str], rows: &[Vec<String>]) -> String {
    let mut output = String::new();
    output.push_str(&headers.join("\t"));
    output.push('\n');
    for row in rows {
        output.push_str(&row.join("\t"));
        output.push('\n');
    }
    output
}

fn render_row(output: &mut String, row: &[String], widths: &[usize]) {
    output.push('|');
    for (index, cell) in row.iter().enumerate() {
        let width = match widths.get(index) {
            Some(value) => *value,
            None => 0,
        };
        output.push(' ');
        output.push_str(cell);
        let padding = width.saturating_sub(cell.chars().count());
        for _ in 0..padding {
            output.push(' ');
        }
        output.push(' ');
        output.push('|');
    }
    output.push('\n');
}

fn render_separator(output: &mut String, widths: &[usize]) {
    output.push('|');
    for width in widths {
        output.push(' ');
        for _ in 0..*width {
            output.push('-');
        }
        output.push(' ');
        output.push('|');
    }
    output.push('\n');
}
