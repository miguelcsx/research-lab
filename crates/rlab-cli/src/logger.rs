use std::sync::atomic::{AtomicU8, Ordering};

use clap::ValueEnum;

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
    use super::LogLevel;
    use clap::ValueEnum;

    #[test]
    fn parses_case_insensitive_levels() {
        assert_eq!(
            LogLevel::from_str("DEBUG", true).ok(),
            Some(LogLevel::Debug)
        );
    }
}
