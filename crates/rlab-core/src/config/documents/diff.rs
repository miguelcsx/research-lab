use std::collections::BTreeSet;

use serde_json::{Map, Value};

use super::ResolvedDocument;

pub fn diff_documents(left: &ResolvedDocument, right: &ResolvedDocument) -> Value {
    diff_values(&left.value, &right.value)
}

fn diff_values(left: &Value, right: &Value) -> Value {
    match (left, right) {
        (Value::Object(left), Value::Object(right)) => diff_objects(left, right),
        _ if left == right => Value::Null,
        _ => changed_value(left, right),
    }
}

fn diff_objects(left: &Map<String, Value>, right: &Map<String, Value>) -> Value {
    let keys = left
        .keys()
        .map(String::as_str)
        .chain(right.keys().map(String::as_str))
        .collect::<BTreeSet<_>>();

    let mut result = Map::new();

    for key in keys {
        let difference = diff_object_field(left, right, key);

        if difference != Value::Null {
            result.insert(key.to_string(), difference);
        }
    }

    if result.is_empty() {
        Value::Null
    } else {
        Value::Object(result)
    }
}

fn diff_object_field(left: &Map<String, Value>, right: &Map<String, Value>, key: &str) -> Value {
    match (left.get(key), right.get(key)) {
        (Some(before), Some(after)) => diff_values(before, after),
        (Some(before), None) => changed_with_missing_after(before),
        (None, Some(after)) => changed_with_missing_before(after),
        (None, None) => Value::Null,
    }
}

fn changed_value(before: &Value, after: &Value) -> Value {
    let mut result = Map::with_capacity(2);
    result.insert("before".to_string(), before.clone());
    result.insert("after".to_string(), after.clone());

    Value::Object(result)
}

fn changed_with_missing_before(after: &Value) -> Value {
    let mut result = Map::with_capacity(2);
    result.insert("before".to_string(), Value::Null);
    result.insert("after".to_string(), after.clone());

    Value::Object(result)
}

fn changed_with_missing_after(before: &Value) -> Value {
    let mut result = Map::with_capacity(2);
    result.insert("before".to_string(), before.clone());
    result.insert("after".to_string(), Value::Null);

    Value::Object(result)
}
