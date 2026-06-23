use rlab_core::{
    config::ProjectPaths, host::validate_event, EffectiveConfig, HostCommand, HostEvent,
    HostRequest, HostTarget, ProtocolVersion, Registry, RegistryKind, RlabResult, RunDirectory,
    RunSession,
};
use serde_json::Value;

use super::process::run_python_host;
use crate::logger;

pub struct ExecutionRequest<'a> {
    pub config: &'a EffectiveConfig,
    pub paths: &'a ProjectPaths,
    pub operation: &'a str,
    pub name: &'a str,
    pub target_kind: RegistryKind,
    pub target_name: &'a str,
    pub params: Value,
    pub seed: Option<u64>,
    pub strict: bool,
    pub default_result: Value,
}

pub struct ExecutionOutcome {
    pub run: RunDirectory,
    pub failed: bool,
}

pub fn execute_run(request: ExecutionRequest<'_>) -> RlabResult<ExecutionOutcome> {
    let seed = request.seed.or(request.config.run.default_seed);
    let params = with_seed(
        with_run_params(&request.config.run.params, request.params),
        seed,
    );
    logger::debug(format!(
        "{} {} -> {}:{}",
        request.operation,
        request.name,
        request.target_kind.as_str(),
        request.target_name
    ));
    let session = RunSession::create(
        request.paths,
        request.operation,
        request.name,
        std::env::args().collect(),
        params.clone(),
    )?;
    let run_id = session.directory.id.as_str().to_string();
    let host_request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: run_id.clone(),
        command: HostCommand::Execute,
        project_root: request.config.project.root.clone(),
        modules: request.config.python.modules.clone(),
        target: Some(HostTarget {
            kind: request.target_kind,
            name: request.target_name.to_string(),
        }),
        run_id: Some(run_id),
        run_dir: Some(session.directory.path.clone()),
        cache_dir: Some(request.paths.cache.clone()),
        params,
        seed,
        strict: request.strict || request.config.production.strict,
        environment: Value::Object(serde_json::Map::new()),
    };
    logger::debug(format!(
        "starting Python host with {} module(s)",
        host_request.modules.len()
    ));
    let _activity =
        logger::start_activity(format!("running {}:{}", request.operation, request.name));
    let events = run_python_host(
        &request.config.python.executable,
        &request.config.python.runner_module,
        &host_request,
        &request.config.run.env,
    )?;
    finalize_session(session, &events, request.default_result)
}

pub fn discover_registry(config: &EffectiveConfig, strict: bool) -> RlabResult<Registry> {
    logger::info(format!(
        "discovering project registry from {} module(s)",
        config.python.modules.len()
    ));
    let host_request = HostRequest {
        protocol_version: ProtocolVersion::current(),
        request_id: "discover".to_string(),
        command: HostCommand::Discover,
        project_root: config.project.root.clone(),
        modules: config.python.modules.clone(),
        target: None,
        run_id: None,
        run_dir: None,
        cache_dir: None,
        params: serde_json::json!({}),
        seed: None,
        strict,
        environment: serde_json::json!({
            "python_executable": config.python.executable,
            "runner_module": config.python.runner_module,
        }),
    };
    let events = run_python_host(
        &config.python.executable,
        &config.python.runner_module,
        &host_request,
        &config.run.env,
    )?;
    let registry = collect_registry(&events)?;
    logger::debug(format!(
        "discovered {} registry record(s)",
        registry.records.len()
    ));
    Ok(registry)
}

pub fn finalize_session(
    session: RunSession,
    events: &[HostEvent],
    default_result: Value,
) -> RlabResult<ExecutionOutcome> {
    let mut completed = None;
    let mut failed = None;
    for event in events {
        process_event(&session, event, &mut completed, &mut failed)?;
    }
    if let Some(error) = failed {
        logger::debug(format!("run {} failed", session.directory.id.as_str()));
        let run = session.fail(&error.to_string())?;
        return Ok(ExecutionOutcome { run, failed: true });
    }
    let run = session.complete(completed.unwrap_or(default_result))?;
    logger::debug(format!("run {} completed", run.id.as_str()));
    Ok(ExecutionOutcome { run, failed: false })
}

pub fn process_event(
    session: &RunSession,
    event: &HostEvent,
    completed: &mut Option<Value>,
    failed: &mut Option<Value>,
) -> RlabResult<()> {
    validate_event(event)?;
    match event {
        HostEvent::Metric(value) => session.append_metric(&value.metric),
        HostEvent::Artifact(value) => session.save_artifact_reference(&value.artifact),
        HostEvent::Log(value) | HostEvent::Warning(value) | HostEvent::Error(value) => {
            session.append_log(&value.message)
        }
        HostEvent::Progress(value) => session.append_log(&crate::logger::progress_message(
            &value.phase,
            &value.component,
            &value.state,
            value.processed,
            value.total,
            &value.unit,
            &value.message,
            &value.detail,
        )),
        HostEvent::Completed { result, .. } => {
            *completed = Some(result.clone());
            Ok(())
        }
        HostEvent::Failed { error, .. } => {
            *failed = Some(error.clone());
            Ok(())
        }
        HostEvent::Batch { events, .. } => {
            for nested in events {
                process_event(session, nested, completed, failed)?;
            }
            Ok(())
        }
        HostEvent::RegistryRecord(_) => Ok(()),
    }
}

pub fn collect_registry(events: &[HostEvent]) -> RlabResult<Registry> {
    let mut registry = Registry::new();
    for event in events {
        collect_registry_event(event, &mut registry)?;
    }
    Ok(registry)
}

fn collect_registry_event(event: &HostEvent, registry: &mut Registry) -> RlabResult<()> {
    validate_event(event)?;
    match event {
        HostEvent::RegistryRecord(record) => registry.insert(record.record.clone()),
        HostEvent::Failed { error, .. } => Err(rlab_core::RlabError::Host {
            message: error.to_string(),
        }),
        HostEvent::Batch { events, .. } => {
            for nested in events {
                collect_registry_event(nested, registry)?;
            }
            Ok(())
        }
        _ => Ok(()),
    }
}

pub(crate) fn with_seed(params: Value, seed: Option<u64>) -> Value {
    let mut object = match params {
        Value::Object(object) => object,
        _ => serde_json::Map::new(),
    };
    if let Some(seed) = seed {
        object.insert("seed".to_string(), Value::from(seed));
    }
    Value::Object(object)
}

pub(crate) fn with_run_params(
    defaults: &std::collections::BTreeMap<String, Value>,
    params: Value,
) -> Value {
    if defaults.is_empty() {
        return params;
    }
    let mut object = serde_json::Map::new();
    object.extend(
        defaults
            .iter()
            .map(|(key, value)| (key.clone(), value.clone())),
    );
    if let Value::Object(params) = params {
        object.extend(params);
    }
    Value::Object(object)
}
