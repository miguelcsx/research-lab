use std::collections::BTreeMap;

const SAFE_ENV_KEYS: [&str; 6] = ["PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "CUDA_VISIBLE_DEVICES"];

pub fn safe_environment(base: &BTreeMap<String, String>, extra: &BTreeMap<String, String>) -> BTreeMap<String, String> {
    let mut env = base
        .iter()
        .filter(|(key, _value)| SAFE_ENV_KEYS.iter().any(|safe| key.as_str() == *safe))
        .map(|(key, value)| (key.clone(), value.clone()))
        .collect::<BTreeMap<_, _>>();
    for (key, value) in extra {
        env.insert(key.clone(), value.clone());
    }
    env
}
