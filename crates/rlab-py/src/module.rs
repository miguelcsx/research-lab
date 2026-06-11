use pyo3::prelude::*;

use crate::py_artifact::{PyArtifactManifest, PyArtifactStore};
use crate::py_cli::cli_main;
use crate::py_config::{find_project_root_py, load_config_py, PyEffectiveConfig};
use crate::py_external::run_external_command_py;
use crate::py_project::PyProjectCore;
use crate::py_registry::{PyRegistry, PyRegistryRecord};
use crate::py_result::{bundle_from_metrics, PyMetric, PyResultBundle};
use crate::py_run::{PyRunDirectory, PyRuntimeContext};
use crate::py_strict::PyProductionPolicy;

pub fn register(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    register_functions(module)?;
    register_classes(module)
}

fn register_functions(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(cli_main, module)?)?;
    module.add_function(wrap_pyfunction!(find_project_root_py, module)?)?;
    module.add_function(wrap_pyfunction!(load_config_py, module)?)?;
    module.add_function(wrap_pyfunction!(bundle_from_metrics, module)?)?;
    module.add_function(wrap_pyfunction!(run_external_command_py, module)?)?;

    Ok(())
}

fn register_classes(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyEffectiveConfig>()?;
    module.add_class::<PyProjectCore>()?;
    module.add_class::<PyRegistry>()?;
    module.add_class::<PyRegistryRecord>()?;
    module.add_class::<PyMetric>()?;
    module.add_class::<PyResultBundle>()?;
    module.add_class::<PyRuntimeContext>()?;
    module.add_class::<PyRunDirectory>()?;
    module.add_class::<PyArtifactManifest>()?;
    module.add_class::<PyArtifactStore>()?;
    module.add_class::<PyProductionPolicy>()?;

    Ok(())
}
