use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PiiHit {
    pub kind: String,
    pub value: String,
}

pub fn scan_for_pii(text: &str) -> Vec<PiiHit> {
    let mut hits = Vec::new();
    for token in text.split_whitespace() {
        let trimmed = token.trim_matches(|ch: char| {
            !ch.is_ascii_alphanumeric() && ch != '@' && ch != '.' && ch != '-' && ch != '_'
        });
        if looks_like_email(trimmed) {
            hits.push(PiiHit {
                kind: "email".to_string(),
                value: trimmed.to_string(),
            });
        }
        if looks_like_ipv4(trimmed) {
            hits.push(PiiHit {
                kind: "ip_address".to_string(),
                value: trimmed.to_string(),
            });
        }
    }
    hits
}

fn looks_like_email(value: &str) -> bool {
    let Some((local, domain)) = value.split_once('@') else {
        return false;
    };
    !local.is_empty() && domain.contains('.') && !domain.starts_with('.') && !domain.ends_with('.')
}

fn looks_like_ipv4(value: &str) -> bool {
    let mut count = 0usize;
    for part in value.split('.') {
        count += 1;
        if part.is_empty() || part.len() > 3 || part.parse::<u8>().is_err() {
            return false;
        }
    }
    count == 4
}
