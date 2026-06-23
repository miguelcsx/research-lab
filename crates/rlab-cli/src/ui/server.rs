use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc,
};
use std::time::Duration;

use rlab_core::{config::ProjectPaths, RlabError, RlabResult};
use tiny_http::{Header, Response, Server, StatusCode};

use super::routes;

pub struct ServerOptions {
    pub port: u16,
    pub open_browser: bool,
    pub as_json: bool,
}

pub trait ServerPrinter {
    fn started(&self, url: &str) -> RlabResult<()>;
    fn warning(&self, message: &str);
    fn stopped(&self);
}

pub fn run<P: ServerPrinter>(
    paths: ProjectPaths,
    options: ServerOptions,
    printer: P,
) -> RlabResult<u8> {
    let address = format!("127.0.0.1:{}", options.port);
    let server = Server::http(&address).map_err(|error| RlabError::Run {
        message: format!("failed to bind rlab ui on {address}: {error}"),
    })?;
    let url = format!("http://{}", server.server_addr());
    printer.started(&url)?;
    if options.open_browser {
        open_url(&url);
    }
    let shutting_down = Arc::new(AtomicBool::new(false));
    install_ctrlc_handler(Arc::clone(&shutting_down))?;
    while !shutting_down.load(Ordering::SeqCst) {
        match server.recv_timeout(Duration::from_millis(100)) {
            Ok(Some(request)) => {
                if let Err(error) = respond(request, &paths) {
                    printer.warning(&error.to_string());
                }
            }
            Ok(None) => {}
            Err(error) => {
                return Err(RlabError::Run {
                    message: format!("rlab ui connection failed: {error}"),
                });
            }
        }
    }
    printer.stopped();
    Ok(0)
}

fn respond(request: tiny_http::Request, paths: &ProjectPaths) -> RlabResult<()> {
    let response = match routes::dispatch(paths, request.url()) {
        Ok(response) => response,
        Err(error) => routes::UiResponse {
            status: 500,
            content_type: "text/html; charset=utf-8",
            body: format!(
                "<!doctype html><meta charset=\"utf-8\"><title>rlab error</title><body><h1>rlab ui error</h1><p>{}</p></body>",
                escape(&error.to_string())
            )
            .into_bytes(),
        },
    };
    let mut http_response =
        Response::from_data(response.body).with_status_code(StatusCode(response.status));
    http_response.add_header(content_type(response.content_type)?);
    request
        .respond(http_response)
        .map_err(|error| RlabError::Run {
            message: format!("failed to write ui response: {error}"),
        })
}

fn content_type(value: &str) -> RlabResult<Header> {
    Header::from_bytes("Content-Type", value).map_err(|_| RlabError::Run {
        message: format!("failed to build content-type header: {value}"),
    })
}

fn install_ctrlc_handler(shutting_down: Arc<AtomicBool>) -> RlabResult<()> {
    ctrlc::set_handler(move || {
        shutting_down.store(true, Ordering::SeqCst);
    })
    .map_err(|error| RlabError::Run {
        message: format!("failed to install Ctrl-C handler: {error}"),
    })
}

fn open_url(url: &str) {
    let mut command = if cfg!(target_os = "macos") {
        let mut command = std::process::Command::new("open");
        command.arg(url);
        command
    } else if cfg!(target_os = "windows") {
        let mut command = std::process::Command::new("cmd");
        command.arg("/C").arg("start").arg(url);
        command
    } else {
        let mut command = std::process::Command::new("xdg-open");
        command.arg(url);
        command
    };
    let _ = command.status();
}

fn escape(value: &str) -> String {
    value
        .replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}
