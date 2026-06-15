use std::collections::BTreeMap;

use pyo3::prelude::*;

#[pyclass(name = "Assumption")]
#[derive(Clone)]
pub struct PyAssumption {
    text: String,
    evidence: Option<String>,
}

#[pymethods]
impl PyAssumption {
    #[new]
    #[pyo3(signature = (text, evidence=None))]
    pub fn new(text: String, evidence: Option<String>) -> Self {
        Self { text, evidence }
    }

    #[getter]
    pub fn text(&self) -> String {
        self.text.clone()
    }

    #[getter]
    pub fn evidence(&self) -> Option<String> {
        self.evidence.clone()
    }
}

#[pyclass(name = "Threat")]
#[derive(Clone)]
pub struct PyThreat {
    text: String,
    mitigation: Option<String>,
}

#[pymethods]
impl PyThreat {
    #[new]
    #[pyo3(signature = (text, mitigation=None))]
    pub fn new(text: String, mitigation: Option<String>) -> Self {
        Self { text, mitigation }
    }

    #[getter]
    pub fn text(&self) -> String {
        self.text.clone()
    }

    #[getter]
    pub fn mitigation(&self) -> Option<String> {
        self.mitigation.clone()
    }
}

#[pyclass(name = "SecretHit")]
#[derive(Clone)]
pub struct PySecretHit {
    hit: rlab_core::SecretHit,
}

#[pymethods]
impl PySecretHit {
    #[getter]
    pub fn key(&self) -> String {
        self.hit.key.clone()
    }

    #[getter]
    pub fn reason(&self) -> String {
        self.hit.reason.clone()
    }
}

impl From<rlab_core::SecretHit> for PySecretHit {
    fn from(hit: rlab_core::SecretHit) -> Self {
        Self { hit }
    }
}

#[pyclass(name = "PiiHit")]
#[derive(Clone)]
pub struct PyPiiHit {
    hit: rlab_core::PiiHit,
}

#[pymethods]
impl PyPiiHit {
    #[getter]
    pub fn kind(&self) -> String {
        self.hit.kind.clone()
    }

    #[getter]
    pub fn value(&self) -> String {
        self.hit.value.clone()
    }
}

impl From<rlab_core::PiiHit> for PyPiiHit {
    fn from(hit: rlab_core::PiiHit) -> Self {
        Self { hit }
    }
}

#[pyclass(name = "LicenseManifest")]
#[derive(Clone)]
pub struct PyLicenseManifest {
    manifest: rlab_core::LicenseManifest,
}

#[pymethods]
impl PyLicenseManifest {
    #[new]
    pub fn new(name: String, license: String) -> Self {
        Self {
            manifest: rlab_core::LicenseManifest {
                schema_version: 1,
                name,
                license,
            },
        }
    }

    #[getter]
    pub fn name(&self) -> String {
        self.manifest.name.clone()
    }

    #[getter]
    pub fn license(&self) -> String {
        self.manifest.license.clone()
    }
}

#[pyclass(name = "LicenseCompatibilitySummary")]
#[derive(Clone)]
pub struct PyLicenseCompatibilitySummary {
    summary: rlab_core::LicenseCompatibilitySummary,
}

#[pymethods]
impl PyLicenseCompatibilitySummary {
    #[getter]
    pub fn compatible(&self) -> bool {
        self.summary.compatible
    }

    #[getter]
    pub fn warnings(&self) -> Vec<String> {
        self.summary.warnings.clone()
    }
}

impl From<rlab_core::LicenseCompatibilitySummary> for PyLicenseCompatibilitySummary {
    fn from(summary: rlab_core::LicenseCompatibilitySummary) -> Self {
        Self { summary }
    }
}

#[pyclass(name = "PolicyViolation")]
#[derive(Clone)]
pub struct PyPolicyViolation {
    violation: rlab_core::PolicyViolation,
}

#[pymethods]
impl PyPolicyViolation {
    #[getter]
    pub fn rule(&self) -> String {
        self.violation.rule.clone()
    }

    #[getter]
    pub fn subject(&self) -> String {
        self.violation.subject.clone()
    }
}

impl From<rlab_core::PolicyViolation> for PyPolicyViolation {
    fn from(violation: rlab_core::PolicyViolation) -> Self {
        Self { violation }
    }
}

#[pyclass(name = "LabPolicy")]
#[derive(Clone)]
pub struct PyLabPolicy {
    policy: rlab_core::LabPolicy,
}

#[pymethods]
impl PyLabPolicy {
    #[new]
    #[pyo3(signature = (forbidden_env_patterns=None))]
    pub fn new(forbidden_env_patterns: Option<Vec<String>>) -> Self {
        let mut policy = rlab_core::LabPolicy::default_policy();
        if let Some(patterns) = forbidden_env_patterns {
            policy.forbidden_env_patterns = patterns;
        }
        Self { policy }
    }

    #[getter]
    pub fn forbidden_env_patterns(&self) -> Vec<String> {
        self.policy.forbidden_env_patterns.clone()
    }

    pub fn check_env(&self, env: BTreeMap<String, String>) -> Vec<PyPolicyViolation> {
        self.policy
            .check_env(&env)
            .into_iter()
            .map(PyPolicyViolation::from)
            .collect()
    }
}

#[pyfunction(name = "redact_secrets")]
pub fn redact_secrets_py(env: BTreeMap<String, String>) -> BTreeMap<String, String> {
    rlab_core::redact_secrets(&env)
}

#[pyfunction(name = "scan_for_secrets")]
pub fn scan_for_secrets_py(text: &str) -> Vec<PySecretHit> {
    rlab_core::scan_for_secrets(text)
        .into_iter()
        .map(PySecretHit::from)
        .collect()
}

#[pyfunction(name = "scan_for_pii")]
pub fn scan_for_pii_py(text: &str) -> Vec<PyPiiHit> {
    rlab_core::scan_for_pii(text)
        .into_iter()
        .map(PyPiiHit::from)
        .collect()
}

#[pyfunction(name = "check_compatibility")]
pub fn check_compatibility_py(
    manifests: Vec<PyRef<'_, PyLicenseManifest>>,
) -> PyLicenseCompatibilitySummary {
    let manifests = manifests
        .iter()
        .map(|manifest| manifest.manifest.clone())
        .collect::<Vec<_>>();
    rlab_core::check_compatibility(&manifests).into()
}
