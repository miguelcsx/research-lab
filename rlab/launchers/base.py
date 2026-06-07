from typing import Protocol

from rlab.external.command import ExternalCommand
from rlab.external.runner import CommandResult


class Launcher(Protocol):
    def launch(self, command: ExternalCommand) -> CommandResult: ...
