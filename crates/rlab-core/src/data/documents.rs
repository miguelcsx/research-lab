use std::collections::BTreeMap;
use std::path::Path;

use serde_json::Value;

use crate::config::{list_documents, resolve_document, validate_documents, ResolvedDocument};
use crate::{RlabError, RlabResult};

use super::model::DataDocument;

const DATA_DOCUMENT_SUFFIX: &str = ".yaml";

pub fn resolve_data_document(
    root: &Path,
    name: &str,
    overrides: BTreeMap<String, Value>,
    require_explicit_paths: bool,
) -> RlabResult<ResolvedDocument> {
    let document = resolve_document(
        root,
        name,
        DATA_DOCUMENT_SUFFIX,
        overrides,
        require_explicit_paths,
    )?;
    validate_data_document_value(&document.value)?;
    Ok(document)
}

pub fn list_data_documents(root: &Path) -> RlabResult<Vec<String>> {
    list_documents(root, DATA_DOCUMENT_SUFFIX)
}

pub fn validate_data_documents(root: &Path) -> RlabResult<BTreeMap<String, String>> {
    let mut failures = validate_documents(root, DATA_DOCUMENT_SUFFIX)?;
    for name in list_data_documents(root)? {
        if failures.contains_key(&name) {
            continue;
        }
        if let Err(error) = resolve_data_document(root, &name, BTreeMap::new(), true) {
            failures.insert(name, error.to_string());
        }
    }
    Ok(failures)
}

fn validate_data_document_value(value: &Value) -> RlabResult<()> {
    let document: DataDocument =
        serde_json::from_value(value.clone()).map_err(RlabError::serialization)?;
    if document.dataset.name.trim().is_empty() {
        return Err(RlabError::Validation {
            message: "data document dataset.name is required".to_string(),
        });
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    fn temp_dir() -> std::path::PathBuf {
        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system clock should be after UNIX_EPOCH")
            .as_nanos();
        let path = std::env::temp_dir().join(format!("rlab-data-docs-{unique}"));
        fs::create_dir_all(&path).expect("create temp data docs dir");
        path
    }

    #[test]
    fn resolves_data_documents_with_extends_and_overrides() {
        let root = temp_dir();
        fs::write(
            root.join("base.yaml"),
            "dataset:\n  name: base\nsource:\n  max_rows: 10\n",
        )
        .expect("write base data doc");
        fs::write(
            root.join("child.yaml"),
            "extends: base\ndataset:\n  name: child\n",
        )
        .expect("write child data doc");

        let document = resolve_data_document(
            &root,
            "child",
            BTreeMap::from([("source.max_rows".to_string(), Value::from(20))]),
            true,
        )
        .expect("resolve data doc");

        assert_eq!(document.value["dataset"]["name"], "child");
        assert_eq!(document.value["source"]["max_rows"], 20);
        assert_eq!(list_data_documents(&root).expect("list data docs").len(), 2);
        assert!(validate_data_documents(&root)
            .expect("validate data docs")
            .is_empty());

        fs::remove_dir_all(root).expect("clean temp data docs dir");
    }
}
