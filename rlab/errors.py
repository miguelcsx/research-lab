class RlabError(Exception):
    """Base error for user-actionable failures."""


class ConfigError(RlabError):
    pass


class RegistryError(RlabError):
    pass


class RegistryConflictError(RegistryError):
    pass


class ReferenceError(RlabError):
    pass


class ModuleLoadError(RlabError):
    pass


class RunError(RlabError):
    pass


class ManifestError(RlabError):
    pass


class ExternalRunError(RlabError):
    pass


class WorkflowError(RlabError):
    pass


class ContractError(RlabError):
    pass


class ValidationError(RlabError):
    pass


class InvalidationError(RlabError):
    pass


class GovernanceError(RlabError):
    pass


class ArtifactError(RlabError):
    pass


class SearchError(RlabError):
    pass
