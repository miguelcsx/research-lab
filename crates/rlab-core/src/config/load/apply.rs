use std::path::PathBuf;

use super::super::model::{EffectiveConfig, DEFAULT_REGISTRY_CACHE_FILE};

pub fn set_cache_paths(config: &mut EffectiveConfig, cache: PathBuf) {
    config.paths.registry_cache = cache.join(DEFAULT_REGISTRY_CACHE_FILE);
    config.paths.cache = cache;
}

pub fn apply_optional_string(target: &mut String, value: Option<String>) {
    if let Some(value) = value {
        *target = value;
    }
}

pub fn apply_optional_vec<T>(target: &mut Vec<T>, value: Option<Vec<T>>) {
    if let Some(value) = value {
        *target = value;
    }
}

pub fn apply_optional_path(target: &mut PathBuf, value: Option<PathBuf>) {
    if let Some(value) = value {
        *target = value;
    }
}

pub fn apply_optional_bool(target: &mut bool, value: Option<bool>) {
    if let Some(value) = value {
        *target = value;
    }
}
