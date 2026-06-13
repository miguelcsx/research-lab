use serde_json::Value;

pub fn merge(base: Value, override_value: Value) -> Value {
    match (base, override_value) {
        (Value::Object(mut base), Value::Object(override_map)) => {
            for (key, value) in override_map {
                let previous = match base.remove(&key) {
                    Some(previous) => previous,
                    None => Value::Null,
                };

                base.insert(key, merge(previous, value));
            }

            Value::Object(base)
        }
        (_, value) => value,
    }
}
