use serde::Serialize;

use rlab_core::error::{RlabError, RlabResult};
use rlab_core::output::JsonEnvelope;

pub fn print_json<T: Serialize>(kind: &str, data: T) -> RlabResult<()> {
    let envelope = JsonEnvelope::new(kind, data);
    let value = serde_json::to_string_pretty(&envelope).map_err(RlabError::serialization)?;
    println!("{value}");
    Ok(())
}
