use std::path::{Component, Path, PathBuf};

use crate::error::{RlabError, RlabResult};

pub fn ensure_child_path(root: &Path, candidate: &Path) -> RlabResult<PathBuf> {
    if candidate.components().any(is_parent_component) {
        return Err(RlabError::Validation {
            message: format!("path contains parent traversal: {}", candidate.display()),
        });
    }
    let root_abs = absolute_without_canonicalizing(root)?;
    let joined = if candidate.is_absolute() {
        candidate.to_path_buf()
    } else {
        root_abs.join(candidate)
    };
    if !joined.starts_with(&root_abs) {
        return Err(RlabError::Validation {
            message: format!("path escapes project root: {}", candidate.display()),
        });
    }
    Ok(joined)
}

pub fn ensure_existing_child_path(root: &Path, candidate: &Path) -> RlabResult<PathBuf> {
    let root_abs = root
        .canonicalize()
        .map_err(|error| RlabError::io(root, error))?;
    let path = ensure_child_path(&root_abs, candidate)?;
    let canonical = path
        .canonicalize()
        .map_err(|error| RlabError::io(&path, error))?;
    if !canonical.starts_with(&root_abs) {
        return Err(RlabError::Validation {
            message: format!(
                "path escapes project root after canonicalization: {}",
                candidate.display()
            ),
        });
    }
    Ok(canonical)
}

fn absolute_without_canonicalizing(path: &Path) -> RlabResult<PathBuf> {
    if path.is_absolute() {
        return Ok(path.to_path_buf());
    }
    let cwd = std::env::current_dir().map_err(|error| RlabError::io(Path::new("."), error))?;
    Ok(cwd.join(path))
}

fn is_parent_component(component: Component<'_>) -> bool {
    matches!(component, Component::ParentDir)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn rejects_parent_traversal() {
        let root = PathBuf::from("/project");
        assert!(ensure_child_path(&root, Path::new("../etc/passwd")).is_err());
        assert!(ensure_child_path(&root, Path::new("a/../../etc")).is_err());
    }

    #[test]
    fn accepts_normal_child_path() {
        let root = PathBuf::from("/project");
        let result = ensure_child_path(&root, Path::new("subdir/file.txt")).unwrap();
        assert!(result.starts_with(&root));
    }

    #[test]
    fn accepts_nested_path() {
        let root = PathBuf::from("/project");
        let result = ensure_child_path(&root, Path::new("a/b/c")).unwrap();
        assert_eq!(result, PathBuf::from("/project/a/b/c"));
    }
}
