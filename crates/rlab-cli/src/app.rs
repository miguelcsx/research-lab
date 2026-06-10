use clap::{Parser, Subcommand};

use rlab_core::RlabResult;

use crate::commands;

#[derive(Debug, Parser)]
#[command(name = "rlab", version, about = "Rust-first local research runtime")]
pub struct Cli {
    #[arg(long, global = true)]
    pub root: Option<std::path::PathBuf>,
    #[arg(long, global = true)]
    pub json: bool,
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Debug, Subcommand)]
pub enum Command {
    Init(commands::init::InitCommand),
    Validate(commands::validate::ValidateCommand),
    Doctor(commands::doctor::DoctorCommand),
    Config(commands::config::ConfigCommand),
    Discover(commands::discover::DiscoverCommand),
    Benchmark(commands::benchmark::BenchmarkCommand),
    Evaluate(commands::evaluate::EvaluateCommand),
    Run(commands::run::RunCommand),
    Runs(commands::runs::RunsCommand),
    Artifact(commands::artifact::ArtifactCommand),
    Compare(commands::compare::CompareCommand),
    Migrate(commands::migrate::MigrateCommand),
    Freeze(commands::freeze::FreezeCommand),
    Cache(commands::cache::CacheCommand),
    Notes(commands::notes::NotesCommand),
    Journal(commands::journal::JournalCommand),
    Report(commands::report::ReportCommand),
    Jobs(commands::jobs::JobsCommand),
    Data(commands::data::DataCommand),
    Graph(commands::graph::GraphCommand),
    Search(commands::search::SearchCommand),
    Lint(commands::lint::LintCommand),
    Ci(commands::ci::CiCommand),
    Baselines(commands::baselines::BaselinesCommand),
    Plan(commands::plan::PlanCommand),
    Errors(commands::errors::ErrorsCommand),
    Table(commands::table::TableCommand),
    Handoff(commands::handoff::HandoffCommand),
    Impact(commands::impact::ImpactCommand),
    Invalidate(commands::invalidate::InvalidateCommand),
    Exec(commands::exec::ExecCommand),
    Modules(commands::modules::ModulesCommand),
    Stats(commands::stats::StatsCommand),
    Study(commands::study::StudyCommand),
    Adapters(commands::adapters::AdaptersCommand),
}

pub fn run_from_env() -> RlabResult<u8> {
    run_from_iter(std::env::args_os())
}

pub fn run_from_iter<I, T>(args: I) -> RlabResult<u8>
where
    I: IntoIterator<Item = T>,
    T: Into<std::ffi::OsString> + Clone,
{
    let cli = Cli::parse_from(args);
    match cli.command {
        Command::Init(command) => commands::init::run(command, cli.root.as_deref(), cli.json),
        Command::Validate(command) => {
            commands::validate::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Doctor(command) => commands::doctor::run(command, cli.root.as_deref(), cli.json),
        Command::Config(command) => commands::config::run(command, cli.root.as_deref(), cli.json),
        Command::Discover(command) => {
            commands::discover::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Benchmark(command) => {
            commands::benchmark::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Evaluate(command) => {
            commands::evaluate::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Run(command) => commands::run::run(command, cli.root.as_deref(), cli.json),
        Command::Runs(command) => commands::runs::run(command, cli.root.as_deref(), cli.json),
        Command::Artifact(command) => {
            commands::artifact::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Compare(command) => commands::compare::run(command, cli.root.as_deref(), cli.json),
        Command::Migrate(command) => commands::migrate::run(command, cli.root.as_deref(), cli.json),
        Command::Freeze(command) => commands::freeze::run(command, cli.root.as_deref(), cli.json),
        Command::Cache(command) => commands::cache::run(command, cli.root.as_deref(), cli.json),
        Command::Notes(command) => commands::notes::run(command, cli.root.as_deref(), cli.json),
        Command::Journal(command) => commands::journal::run(command, cli.root.as_deref(), cli.json),
        Command::Report(command) => commands::report::run(command, cli.root.as_deref(), cli.json),
        Command::Jobs(command) => commands::jobs::run(command, cli.root.as_deref(), cli.json),
        Command::Data(command) => commands::data::run(command, cli.root.as_deref(), cli.json),
        Command::Graph(command) => commands::graph::run(command, cli.root.as_deref(), cli.json),
        Command::Search(command) => commands::search::run(command, cli.root.as_deref(), cli.json),
        Command::Lint(command) => commands::lint::run(command, cli.root.as_deref(), cli.json),
        Command::Ci(command) => commands::ci::run(command, cli.root.as_deref(), cli.json),
        Command::Baselines(command) => {
            commands::baselines::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Plan(command) => commands::plan::run(command, cli.root.as_deref(), cli.json),
        Command::Errors(command) => commands::errors::run(command, cli.root.as_deref(), cli.json),
        Command::Table(command) => commands::table::run(command, cli.root.as_deref(), cli.json),
        Command::Handoff(command) => commands::handoff::run(command, cli.root.as_deref(), cli.json),
        Command::Impact(command) => commands::impact::run(command, cli.root.as_deref(), cli.json),
        Command::Invalidate(command) => {
            commands::invalidate::run(command, cli.root.as_deref(), cli.json)
        }
        Command::Exec(command) => commands::exec::run(command, cli.root.as_deref(), cli.json),
        Command::Modules(command) => commands::modules::run(command, cli.root.as_deref(), cli.json),
        Command::Stats(command) => commands::stats::run(command, cli.root.as_deref(), cli.json),
        Command::Study(command) => commands::study::run(command, cli.root.as_deref(), cli.json),
        Command::Adapters(command) => {
            commands::adapters::run(command, cli.root.as_deref(), cli.json)
        }
    }
}
