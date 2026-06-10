use pyo3::prelude::*;

use crate::error::to_py_error;

#[pyfunction]
pub fn cli_main(py: Python<'_>) -> PyResult<u8> {
    // When called from a Python entry-point script the OS-level argv is
    //   [python_interpreter, script_path, ...user_args]
    // Rust's std::env::args_os() reads that, so clap treats the script
    // path as the first argument (a subcommand), which fails.
    // We read Python's sys.argv instead — it already strips the interpreter
    // — and present args as ["rlab", ...user_args] to clap.
    let sys = py.import("sys")?;
    let argv: Vec<String> = sys.getattr("argv")?.extract()?;
    let effective: Vec<std::ffi::OsString> = std::iter::once(std::ffi::OsString::from("rlab"))
        .chain(argv.into_iter().skip(1).map(Into::into))
        .collect();
    rlab_cli::run_from_iter(effective).map_err(to_py_error)
}
