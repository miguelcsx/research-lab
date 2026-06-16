use std::sync::atomic::{AtomicU8, Ordering};

use clap::ValueEnum;
use rlab_core::HostEvent;

#[derive(Clone, Copy, Debug, Eq, PartialEq, ValueEnum)]
pub enum LogLevel {
    Off,
    Error,
    Warn,
    Info,
    Debug,
}

static LEVEL: AtomicU8 = AtomicU8::new(LogLevel::Off as u8);

pub fn init(json: bool, explicit: Option<LogLevel>) {
    let level =
        explicit
            .or_else(env_level)
            .unwrap_or(if json { LogLevel::Off } else { LogLevel::Info });
    LEVEL.store(level as u8, Ordering::Relaxed);
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

pub fn event(host_event: &HostEvent) {
    match host_event {
        HostEvent::Log(log) => info(&log.message),
        HostEvent::Warning(log) => warn(&log.message),
        HostEvent::Error(log) => error(&log.message),
        HostEvent::Progress(progress) => {
            let level = if progress.state == "running" {
                LogLevel::Debug
            } else {
                LogLevel::Info
            };
            log(
                level,
                progress_message(
                    &progress.phase,
                    &progress.component,
                    &progress.state,
                    progress.processed,
                    progress.total,
                    &progress.detail,
                ),
            );
        }
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
    detail: &str,
) -> String {
    let tag = if component.is_empty() {
        format!("[{phase}]")
    } else {
        format!("[{phase}.{component}]")
    };
    let count = match total {
        Some(total) => format!(" {processed}/{total}"),
        None if processed > 0 => format!(" {processed}"),
        None => String::new(),
    };
    if detail.is_empty() {
        format!("{tag} {state}{count}")
    } else {
        format!("{tag} {state}{count}: {detail}")
    }
}

fn log(level: LogLevel, message: impl AsRef<str>) {
    if (level as u8) <= LEVEL.load(Ordering::Relaxed) {
        eprintln!("rlab {} {}", label(level), message.as_ref());
    }
}

fn env_level() -> Option<LogLevel> {
    std::env::var("RLAB_LOG")
        .ok()
        .and_then(|value| LogLevel::from_str(&value, true).ok())
}

fn label(level: LogLevel) -> &'static str {
    match level {
        LogLevel::Off => "OFF",
        LogLevel::Error => "ERROR",
        LogLevel::Warn => "WARN",
        LogLevel::Info => "INFO",
        LogLevel::Debug => "DEBUG",
    }
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
            progress_message("dataset", "smoke", "completed", 42, Some(100), "wrote rows"),
            "[dataset.smoke] completed 42/100: wrote rows"
        );
    }
}
