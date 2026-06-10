use serde::Serialize;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Serialize)]
pub struct JsonEnvelope<T: Serialize> {
    pub schema_version: u32,
    pub kind: String,
    pub data: T,
}

impl<T: Serialize> JsonEnvelope<T> {
    pub fn new(kind: &str, data: T) -> Self {
        Self { schema_version: SCHEMA_VERSION, kind: kind.to_string(), data }
    }
}
