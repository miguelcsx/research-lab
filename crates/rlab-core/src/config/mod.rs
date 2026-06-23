mod discovery;
mod documents;
mod env;
mod load;
mod model;
mod overrides;
mod paths;
mod validate;

pub use discovery::find_project_root;
pub use documents::{
    apply_dotted_overrides, diff_documents, list_documents, resolve_document, validate_documents,
    ResolvedDocument,
};
pub use load::load_effective_config;
pub use model::{
    EffectiveConfig, MaterializedRetention, OutputRetention, PathConfig, ProductionConfig,
    ProjectConfig, PythonConfig, ReproducibilityConfig, ResumeStateRetention, RunRetention,
    StorageConfig,
};
pub use overrides::ConfigOverride;
pub use paths::ProjectPaths;
pub use validate::{validate_config, validate_lab_schema_version};
