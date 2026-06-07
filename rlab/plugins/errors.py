from rlab.errors import PluginError


class PluginLoadError(PluginError):
    pass


class PluginConflictError(PluginError):
    pass


class PluginVersionError(PluginError):
    pass
