use std::collections::BTreeMap;

pub fn rlab_environment() -> BTreeMap<String, String> {
    std::env::vars()
        .filter(|(key, _)| key.starts_with("RLAB__"))
        .collect()
}
