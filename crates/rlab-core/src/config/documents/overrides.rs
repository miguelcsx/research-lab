use serde_json::Value;

use crate::error::{RlabError, RlabResult};

pub fn set_path(root: &mut Value, path: &str, value: Value) -> RlabResult<()> {
    if path.is_empty() {
        return Err(RlabError::config(format!("invalid config path: {path:?}")));
    }

    let mut target = root;
    let mut parts = path.split('.').peekable();

    while let Some(part) = parts.next() {
        if part.is_empty() {
            return Err(RlabError::config(format!("invalid config path: {path:?}")));
        }

        if parts.peek().is_none() {
            return insert_path_value(target, path, part, value);
        }

        target = descend_path(target, path, part)?;
    }

    Err(RlabError::config(format!("invalid config path: {path:?}")))
}

fn descend_path<'a>(target: &'a mut Value, path: &str, part: &str) -> RlabResult<&'a mut Value> {
    target
        .as_object_mut()
        .and_then(|object| object.get_mut(part))
        .filter(|value| value.is_object())
        .ok_or_else(|| RlabError::config(format!("unknown or non-mapping config path: {path:?}")))
}

fn insert_path_value(target: &mut Value, path: &str, key: &str, value: Value) -> RlabResult<()> {
    let object = target
        .as_object_mut()
        .ok_or_else(|| RlabError::config(format!("config root must be a mapping: {path:?}")))?;

    object.insert(key.to_string(), value);

    Ok(())
}
