use std::fs;

use serde::{Deserialize, Serialize};

use crate::config::ProjectPaths;
use crate::error::{RlabError, RlabResult};
use crate::fs::write_json_atomic;
use crate::run::list_runs;
const SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchDocument {
    pub schema_version: u32,
    pub kind: String,
    pub id: String,
    pub text: String,
}

pub fn build_search_index(paths: &ProjectPaths) -> RlabResult<Vec<SearchDocument>> {
    let mut documents = Vec::new();
    append_run_documents(paths, &mut documents)?;
    append_registry_documents(paths, &mut documents)?;
    append_journal_documents(paths, &mut documents)?;
    write_json_atomic(&paths.cache.join("search_index.json"), &documents)?;
    Ok(documents)
}

fn append_run_documents(
    paths: &ProjectPaths,
    documents: &mut Vec<SearchDocument>,
) -> RlabResult<()> {
    for run in list_runs(paths)? {
        let mut text = format!("{} {} {} {:?}", run.id, run.operation, run.name, run.status);
        for file in ["metrics_summary.json", "results.json", "report.md"] {
            let path = paths.runs.join(&run.id).join(file);
            if path.exists() {
                text.push(' ');
                text.push_str(
                    &fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?,
                );
            }
        }
        documents.push(SearchDocument {
            schema_version: SCHEMA_VERSION,
            kind: "run".to_string(),
            id: run.id,
            text,
        });
    }
    Ok(())
}

fn append_registry_documents(
    paths: &ProjectPaths,
    documents: &mut Vec<SearchDocument>,
) -> RlabResult<()> {
    if !paths.registry_cache.exists() {
        return Ok(());
    }
    let content = fs::read_to_string(&paths.registry_cache)
        .map_err(|error| RlabError::io(&paths.registry_cache, error))?;
    documents.push(SearchDocument {
        schema_version: SCHEMA_VERSION,
        kind: "registry".to_string(),
        id: "registry_cache".to_string(),
        text: content,
    });
    Ok(())
}

fn append_journal_documents(
    paths: &ProjectPaths,
    documents: &mut Vec<SearchDocument>,
) -> RlabResult<()> {
    for name in [
        "decisions.jsonl",
        "negatives.jsonl",
        "ideas.jsonl",
        "notes.jsonl",
    ] {
        let path = paths.cache.join(name);
        if path.exists() {
            let text = fs::read_to_string(&path).map_err(|error| RlabError::io(&path, error))?;
            documents.push(SearchDocument {
                schema_version: SCHEMA_VERSION,
                kind: "journal".to_string(),
                id: name.to_string(),
                text,
            });
        }
    }
    Ok(())
}
