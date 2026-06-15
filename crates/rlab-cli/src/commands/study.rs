use std::collections::BTreeMap;
use std::path::Path;

use clap::{Args, Subcommand};
use rlab_core::{
    config::ProjectPaths, load_effective_config, plan_registry_study, search_project,
    EffectiveConfig, RegistryKind, RegistryStudyPlan, RlabError, RlabResult, RunSession, RunStatus,
    StudyMode,
};
use serde::Serialize;
use serde_json::{Map, Value};

use crate::commands::discover::discover_registry;
use crate::commands::run::{execute_run, parse_params_public, resolve_param_refs};
use crate::render::{human::print_line, json::print_json};

const RESULT_SCHEMA_VERSION: u32 = 1;
const SEARCH_INDEX: &str = "registry";

#[derive(Debug, Args)]
pub struct StudyCommand {
    #[command(subcommand)]
    pub command: StudySubcommand,
}

#[derive(Debug, Subcommand)]
pub enum StudySubcommand {
    List,
    Show { name: String },
    Plan(StudyPlanArgs),
    Run(StudyPlanArgs),
}

#[derive(Debug, Args)]
pub struct StudyPlanArgs {
    name: String,
    #[arg(long)]
    full: bool,
    #[arg(long)]
    strict: bool,
    #[arg(long = "param")]
    params: Vec<String>,
}

#[derive(Debug, Serialize)]
struct ChildRun {
    experiment: String,
    job_id: String,
    run_id: String,
    status: RunStatus,
}

pub fn run(command: StudyCommand, root: Option<&Path>, json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    match command.command {
        StudySubcommand::List => list_studies(&paths, json),
        StudySubcommand::Show { name } => show_study(&paths, &name, json),
        StudySubcommand::Plan(args) => plan_command(&config, &paths, &args, json),
        StudySubcommand::Run(args) => run_study(&config, &paths, &args, json),
    }
}

fn list_studies(paths: &ProjectPaths, json: bool) -> RlabResult<u8> {
    let hits = search_project(paths, RegistryKind::STUDY.as_str(), Some(SEARCH_INDEX))?;
    if json {
        print_json("study_list", hits)?;
    } else {
        for hit in hits {
            print_line(&hit.id);
        }
    }
    Ok(0)
}

fn show_study(paths: &ProjectPaths, name: &str, json: bool) -> RlabResult<u8> {
    let hits = search_project(paths, name, None)?;
    if json {
        print_json("study_show", hits)?;
    } else {
        print_line(&serde_json::to_string_pretty(&hits).map_err(RlabError::serialization)?);
    }
    Ok(0)
}

fn plan_command(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    args: &StudyPlanArgs,
    json: bool,
) -> RlabResult<u8> {
    let plan = load_plan(config, paths, args)?;
    render_plan(&plan, json)?;
    Ok(0)
}

fn run_study(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    args: &StudyPlanArgs,
    json: bool,
) -> RlabResult<u8> {
    let strict = args.strict || config.production.strict;
    let plan = load_plan(config, paths, args)?;
    let session = create_parent_session(paths, &plan)?;

    if !json {
        print_line(&format!(
            "study {}: {} jobs",
            plan.mode.as_str(),
            plan.jobs.len()
        ));
    }

    let mut children = Vec::with_capacity(plan.jobs.len());
    let mut failures = 0usize;
    for job in &plan.jobs {
        let outcome = execute_run(
            config,
            paths,
            &RegistryKind::EXPERIMENT,
            &job.experiment,
            job_params_value(&job.params),
            job.seed,
            strict,
        )?;
        let status = if outcome.failed {
            failures += 1;
            RunStatus::Failed
        } else {
            RunStatus::Completed
        };
        render_child(job, &outcome.run, status, json);
        children.push(ChildRun {
            experiment: job.experiment.clone(),
            job_id: job.job_id.clone(),
            run_id: outcome.run.id.as_str().to_owned(),
            status,
        });
    }

    finish_parent(session, &plan, children, failures, json)
}

fn load_plan(
    config: &EffectiveConfig,
    paths: &ProjectPaths,
    args: &StudyPlanArgs,
) -> RlabResult<RegistryStudyPlan> {
    let strict = args.strict || config.production.strict;
    let registry = discover_registry(config, paths, strict, false)?;
    let explicit = parse_params(&args.params)?;
    let mut plan = plan_registry_study(&registry, &args.name, study_mode(args.full), &explicit)?;
    resolve_plan_refs(paths, &mut plan)?;
    Ok(plan)
}

fn parse_params(params: &[String]) -> RlabResult<BTreeMap<String, Value>> {
    serde_json::from_value(parse_params_public(params)?)
        .map_err(|error| RlabError::validation(format!("invalid study parameters: {error}")))
}

fn study_mode(full: bool) -> StudyMode {
    if full {
        StudyMode::Full
    } else {
        StudyMode::Qualification
    }
}

fn create_parent_session(paths: &ProjectPaths, plan: &RegistryStudyPlan) -> RlabResult<RunSession> {
    RunSession::create(
        paths,
        RegistryKind::STUDY.as_str(),
        &plan.study,
        std::env::args().collect(),
        serde_json::json!({"mode": plan.mode}),
    )
}

fn resolve_job_params(paths: &ProjectPaths, params: &BTreeMap<String, Value>) -> RlabResult<Value> {
    let value = serde_json::to_value(params).map_err(RlabError::serialization)?;
    resolve_param_refs(paths, value)
}

fn resolve_plan_refs(paths: &ProjectPaths, plan: &mut RegistryStudyPlan) -> RlabResult<()> {
    for job in &mut plan.jobs {
        job.params = serde_json::from_value(resolve_job_params(paths, &job.params)?)
            .map_err(RlabError::serialization)?;
    }
    Ok(())
}

fn job_params_value(params: &BTreeMap<String, Value>) -> Value {
    let mut object = Map::new();
    object.extend(
        params
            .iter()
            .map(|(key, value)| (key.clone(), value.clone())),
    );
    Value::Object(object)
}

fn render_child(
    job: &rlab_core::ExperimentJob,
    run: &rlab_core::RunDirectory,
    status: RunStatus,
    json: bool,
) {
    if json {
        return;
    }
    print_line(&format!(
        "  {} {}:{} -> {}",
        status.as_str(),
        job.experiment,
        job.job_id,
        run.id.as_str()
    ));
}

fn finish_parent(
    session: RunSession,
    plan: &RegistryStudyPlan,
    children: Vec<ChildRun>,
    failures: usize,
    json: bool,
) -> RlabResult<u8> {
    let result = serde_json::json!({
        "schema_version": RESULT_SCHEMA_VERSION,
        "study": plan.study,
        "mode": plan.mode,
        "runs": children,
        "failures": failures,
    });
    let run = if failures == 0 {
        session.complete(result)?
    } else {
        session.fail_with_result(
            &format!("{failures} of {} study jobs failed", plan.jobs.len()),
            result,
        )?
    };

    if json {
        print_json("study_run", run)?;
    } else {
        print_line(&format!(
            "study complete: {} runs, {} failed -> {}",
            plan.jobs.len(),
            failures,
            run.id.as_str()
        ));
    }
    Ok(u8::from(failures > 0))
}

fn render_plan(plan: &RegistryStudyPlan, json: bool) -> RlabResult<()> {
    if json {
        return print_json("study_plan", plan);
    }
    print_line(&format!(
        "{} study {}: {} jobs",
        plan.mode.as_str(),
        plan.study,
        plan.jobs.len()
    ));
    for job in &plan.jobs {
        let seed = match job.seed {
            Some(value) => value.to_string(),
            None => "none".to_owned(),
        };
        let params = serde_json::to_string(&job.params).map_err(RlabError::serialization)?;
        print_line(&format!(
            "  {}:{} seed={seed} params={params}",
            job.experiment, job.job_id
        ));
    }
    Ok(())
}
