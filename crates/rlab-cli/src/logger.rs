use std::io::IsTerminal;
use std::sync::{
    atomic::{AtomicBool, AtomicU8, Ordering},
    LazyLock, Mutex,
};

use clap::ValueEnum;
use indicatif::{ProgressBar, ProgressStyle};
use rlab_core::{host::ProgressEvent, HostEvent};

#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum LogLevel {
    Off,
    Error,
    Warn,
    Info,
    Debug,
}

static LEVEL: AtomicU8 = AtomicU8::new(LogLevel::Off as u8);
static PROGRESS_ENABLED: AtomicBool = AtomicBool::new(false);
static PROGRESS: LazyLock<Mutex<Option<ProgressBar>>> = LazyLock::new(|| Mutex::new(None));
static ACTIVITY: LazyLock<Mutex<Option<ProgressBar>>> = LazyLock::new(|| Mutex::new(None));

pub struct ActivityGuard {
    active: bool,
}

impl Drop for ActivityGuard {
    fn drop(&mut self) {
        if self.active {
            clear_activity();
        }
    }
}

pub fn init(json: bool, quiet: bool, explicit: Option<LogLevel>) {
    let level = if quiet {
        LogLevel::Off
    } else {
        explicit
            .or_else(env_level)
            .unwrap_or(if json { LogLevel::Off } else { LogLevel::Info })
    };
    LEVEL.store(level as u8, Ordering::Relaxed);
    PROGRESS_ENABLED.store(
        !json && !quiet && (LogLevel::Info as u8) <= level as u8 && std::io::stderr().is_terminal(),
        Ordering::Relaxed,
    );
}

pub fn error(message: impl AsRef<str>) {
    log(LogLevel::Error, message);
}

pub fn warn(message: impl AsRef<str>) {
    log(LogLevel::Warn, message);
}

pub fn info(message: impl AsRef<str>) {
    log(LogLevel::Info, message);
}

pub fn debug(message: impl AsRef<str>) {
    log(LogLevel::Debug, message);
}

pub fn start_activity(message: impl Into<String>) -> ActivityGuard {
    if !PROGRESS_ENABLED.load(Ordering::Relaxed) {
        return ActivityGuard { active: false };
    }
    let bar = ProgressBar::new_spinner();
    bar.set_style(activity_style());
    bar.set_prefix("rlab");
    bar.set_message(message.into());
    bar.enable_steady_tick(std::time::Duration::from_millis(90));
    let mut guard = ACTIVITY.lock().expect("activity mutex poisoned");
    if let Some(previous) = guard.take() {
        previous.finish_and_clear();
    }
    *guard = Some(bar);
    ActivityGuard { active: true }
}

pub fn event(host_event: &HostEvent) {
    match host_event {
        HostEvent::Log(log) => info(&log.message),
        HostEvent::Warning(log) => warn(&log.message),
        HostEvent::Error(log) => error(&log.message),
        HostEvent::Progress(progress) => progress_event(progress),
        HostEvent::Batch { events, .. } => {
            for nested in events {
                event(nested);
            }
        }
        _ => {}
    }
}

pub fn progress_message(
    phase: &str,
    component: &str,
    state: &str,
    processed: u64,
    total: Option<u64>,
    unit: &str,
    message: &str,
    detail: &str,
) -> String {
    let tag = if component.is_empty() {
        format!("[{phase}]")
    } else {
        format!("[{phase}.{component}]")
    };
    let count = match total {
        Some(total) if unit.is_empty() => format!(" {processed}/{total}"),
        Some(total) => format!(" {processed}/{total} {unit}"),
        None if processed > 0 && unit.is_empty() => format!(" {processed}"),
        None if processed > 0 => format!(" {processed} {unit}"),
        None => String::new(),
    };
    let text = if message.is_empty() { detail } else { message };
    if text.is_empty() {
        format!("{tag} {state}{count}")
    } else {
        format!("{tag} {state}{count}: {text}")
    }
}

fn progress_event(progress: &ProgressEvent) {
    if !PROGRESS_ENABLED.load(Ordering::Relaxed) {
        log(
            LogLevel::Info,
            progress_message(
                &progress.phase,
                &progress.component,
                &progress.state,
                progress.processed,
                progress.total,
                &progress.unit,
                &progress.message,
                &progress.detail,
            ),
        );
        return;
    }

    let Some(total) = progress.total else {
        update_activity(progress_label(progress));
        if progress.state != "running" {
            clear_activity();
            info(progress_message(
                &progress.phase,
                &progress.component,
                &progress.state,
                progress.processed,
                progress.total,
                &progress.unit,
                &progress.message,
                &progress.detail,
            ));
        }
        return;
    };

    clear_activity();
    let mut guard = PROGRESS.lock().expect("progress mutex poisoned");
    let bar = guard.get_or_insert_with(|| {
        let bar = ProgressBar::new(total);
        bar.set_style(progress_style());
        bar.set_prefix("rlab progress");
        bar
    });
    bar.set_length(total);
    bar.set_position(progress.processed.min(total));
    bar.set_message(progress_label(progress));
    if progress.state == "running" {
        return;
    }
    let message = progress_message(
        &progress.phase,
        &progress.component,
        &progress.state,
        progress.processed,
        progress.total,
        &progress.unit,
        &progress.message,
        &progress.detail,
    );
    bar.finish_and_clear();
    *guard = None;
    drop(guard);
    info(message);
}

fn progress_style() -> ProgressStyle {
    ProgressStyle::with_template("{prefix:.cyan.bold} {bar:32.cyan/blue} {pos}/{len} {msg}")
        .unwrap_or_else(|_| ProgressStyle::default_bar())
        .progress_chars("=> ")
}

fn activity_style() -> ProgressStyle {
    ProgressStyle::with_template("{spinner:.cyan} {prefix:.cyan.bold} {msg} {elapsed_precise}")
        .unwrap_or_else(|_| ProgressStyle::default_spinner())
        .tick_chars("-\\|/")
}

fn update_activity(message: String) {
    let guard = ACTIVITY.lock().expect("activity mutex poisoned");
    if let Some(bar) = guard.as_ref() {
        bar.set_message(message);
    }
}

fn clear_activity() {
    let mut guard = ACTIVITY.lock().expect("activity mutex poisoned");
    if let Some(bar) = guard.take() {
        bar.finish_and_clear();
    }
}

fn progress_label(progress: &ProgressEvent) -> String {
    let tag = if progress.component.is_empty() {
        progress.phase.clone()
    } else {
        format!("{}.{}", progress.phase, progress.component)
    };
    let text = if progress.message.is_empty() {
        &progress.detail
    } else {
        &progress.message
    };
    if text.is_empty() {
        tag
    } else {
        format!("{tag}: {text}")
    }
}

fn log(level: LogLevel, message: impl AsRef<str>) {
    if (level as u8) <= LEVEL.load(Ordering::Relaxed) {
        eprintln!(
            "{} {} {}",
            paint_stderr("rlab", "1;36"),
            label(level),
            message.as_ref()
        );
    }
}

fn env_level() -> Option<LogLevel> {
    std::env::var("RLAB_LOG")
        .ok()
        .and_then(|value| LogLevel::from_str(&value, true).ok())
}

fn label(level: LogLevel) -> String {
    match level {
        LogLevel::Off => paint_stderr("OFF", "2"),
        LogLevel::Error => paint_stderr("error", "31"),
        LogLevel::Warn => paint_stderr("warn", "33"),
        LogLevel::Info => paint_stderr("info", "32"),
        LogLevel::Debug => paint_stderr("debug", "34"),
    }
}

fn paint_stderr(value: &str, code: &str) -> String {
    if stderr_color_enabled() {
        format!("\x1b[{code}m{value}\x1b[0m")
    } else {
        value.to_string()
    }
}

fn stderr_color_enabled() -> bool {
    match std::env::var("RLAB_COLOR").ok().as_deref() {
        Some("always" | "1" | "true") => return true,
        Some("never" | "0" | "false") => return false,
        _ => {}
    }
    if std::env::var_os("NO_COLOR").is_some() {
        return false;
    }
    if std::env::var("TERM").ok().as_deref() == Some("dumb") {
        return false;
    }
    std::io::stderr().is_terminal()
}

#[cfg(test)]
mod tests {
    use super::{progress_message, LogLevel};
    use clap::ValueEnum;

    #[test]
    fn parses_case_insensitive_levels() {
        assert_eq!(
            LogLevel::from_str("DEBUG", true).ok(),
            Some(LogLevel::Debug)
        );
    }

    #[test]
    fn formats_progress_with_counts() {
        assert_eq!(
            progress_message(
                "run",
                "smoke",
                "completed",
                42,
                Some(100),
                "items",
                "",
                "wrote outputs"
            ),
            "[run.smoke] completed 42/100 items: wrote outputs"
        );
    }
}
