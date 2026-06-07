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


class PluginError(RlabError):
    pass


class RunError(RlabError):
    pass


class ManifestError(RlabError):
    pass


class ExternalRunError(RlabError):
    pass
