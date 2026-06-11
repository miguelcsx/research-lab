const SECRET_MARKERS: &[&str] = &[
    "token",
    "secret",
    "password",
    "credential",
    "api_key",
    "apikey",
    "key",
];
const REDACTED: &str = "<redacted>";

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SafeMessage(pub String);

pub fn redact_secrets(input: &str) -> String {
    input
        .lines()
        .map(redact_line)
        .collect::<Vec<String>>()
        .join("\n")
}

fn redact_line(line: &str) -> String {
    let lower = line.to_ascii_lowercase();
    if SECRET_MARKERS.iter().any(|marker| lower.contains(marker)) {
        return REDACTED.to_string();
    }
    line.to_string()
}
