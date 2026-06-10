fn main() -> std::process::ExitCode {
    match rlab_cli::run_from_env() {
        Ok(code) => std::process::ExitCode::from(code),
        Err(error) => {
            eprintln!("{error}");
            std::process::ExitCode::FAILURE
        }
    }
}
