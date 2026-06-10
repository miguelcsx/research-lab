use std::fs;

use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};

use super::index::{build_search_index, SearchDocument};
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchHit {
    pub schema_version: u32,
    pub kind: String,
    pub id: String,
    pub score: u32,
    pub snippet: String,
}

pub fn search_project(paths: &ProjectPaths, term: &str, kind: Option<&str>) -> RlabResult<Vec<SearchHit>> {
    let index_path = paths.cache.join("search_index.json");
    let documents = if index_path.exists() {
        let content = fs::read_to_string(&index_path).map_err(|error| RlabError::io(&index_path, error))?;
        serde_json::from_str::<Vec<SearchDocument>>(&content).map_err(RlabError::serialization)?
    } else {
        build_search_index(paths)?
    };
    let needle = term.to_lowercase();
    let mut hits = documents
        .into_iter()
        .filter(|document| match kind { Some(expected) => document.kind == expected, None => true })
        .filter_map(|document| {
            let text = document.text.to_lowercase();
            let score = text.matches(&needle).count() as u32;
            if score == 0 {
                None
            } else {
                Some(SearchHit { schema_version: SCHEMA_VERSION, kind: document.kind, id: document.id, score, snippet: document.text.chars().take(240).collect() })
            }
        })
        .collect::<Vec<_>>();
    hits.sort_by(|left, right| right.score.cmp(&left.score));
    Ok(hits)
}
