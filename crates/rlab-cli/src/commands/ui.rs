use std::path::Path;

use clap::Args;
use rlab_core::{config::ProjectPaths, load_effective_config, RlabResult};

use crate::render::{human::print_line, json::print_json};

#[derive(Debug, Args)]
pub struct UiCommand {
    #[arg(long, default_value_t = 8787)]
    pub port: u16,
    #[arg(long)]
    pub no_open: bool,
}

pub fn run(command: UiCommand, root: Option<&Path>, as_json: bool) -> RlabResult<u8> {
    let config = load_effective_config(root, &[])?;
    let paths = ProjectPaths::from_config(&config)?;
    let options = crate::ui::server::ServerOptions {
        port: command.port,
        open_browser: !command.no_open,
        as_json,
    };
    crate::ui::server::run(paths, options, UiPrinter { as_json })
}

struct UiPrinter {
    as_json: bool,
}

impl crate::ui::server::ServerPrinter for UiPrinter {
    fn started(&self, url: &str) -> RlabResult<()> {
        if self.as_json {
            print_json("ui", serde_json::json!({"url": url}))
        } else {
            print_line(&format!("rlab ui: {url}"));
            Ok(())
        }
    }

    fn warning(&self, message: &str) {
        if !self.as_json {
            print_line(&format!("rlab ui warning: {message}"));
        }
    }

    fn stopped(&self) {
        if !self.as_json {
            print_line("rlab ui: stopped");
        }
    }
}
