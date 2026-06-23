use askama::Template;

use super::views::{
    ArtifactDetail, ArtifactsView, CompareView, ReportBundle, ReportsView, RunDetailView, RunsView,
    SectionsView,
};

#[derive(Template)]
#[template(path = "runs.html")]
pub struct RunsTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: RunsView,
}

#[derive(Template)]
#[template(path = "run.html")]
pub struct RunTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: RunDetailView,
}

#[derive(Template)]
#[template(path = "artifacts.html")]
pub struct ArtifactsTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: ArtifactsView,
}

#[derive(Template)]
#[template(path = "artifact.html")]
pub struct ArtifactTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: ArtifactDetail,
}

#[derive(Template)]
#[template(path = "reports.html")]
pub struct ReportsTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: ReportsView,
}

#[derive(Template)]
#[template(path = "report.html")]
pub struct ReportTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: ReportBundle,
}

#[derive(Template)]
#[template(path = "sections.html")]
pub struct SectionsTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: SectionsView,
}

#[derive(Template)]
#[template(path = "compare.html")]
pub struct CompareTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub view: CompareView,
}

#[derive(Template)]
#[template(path = "error.html")]
pub struct ErrorTemplate {
    pub title: &'static str,
    pub active: &'static str,
    pub message: String,
}
